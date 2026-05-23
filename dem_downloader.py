# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Daniel Hulshof Saint Martin
                                Adaptations (C) 2026 Bortre Tenamo
        email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/


DEM tile download, caching, and merging using Copernicus GLO-30 from AWS.

Portions of this module are adapted from the ContourLines QGIS plugin
by Daniel Hulshof Saint Martin.

Downloads Cloud-Optimized GeoTIFF tiles on demand, caches them locally,
and provides utilities to clip/merge for a given area of interest.
"""

from __future__ import annotations

import logging
import math
import os
import re
import stat
import ssl
import tempfile
import urllib.request
import getpass
from typing import Any


from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
)

from NoWires.geo_bounds import longitude_intervals
from NoWires.tile_download_base import clip_and_merge_tiles, download_tile_with_retry

logger = logging.getLogger(__name__)

COPERNICUS_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/"
_MAX_TILES = 200
_DOWNLOAD_RETRIES = 3
_SOCKET_TIMEOUT = 60
_VALID_TILE_RE = re.compile(r"^Copernicus_DSM_COG_10_[NS]\d{2}_00_[EW]\d{3}_00_DEM$")


def get_temp_dir(create=True):
    try:
        username = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser())
    except (OSError, KeyError):
        username = "nowires"
    base = tempfile.gettempdir()
    target = os.path.join(base, "NoWires-" + username)
    if create:
        try:
            st = os.lstat(target)
            if stat.S_ISLNK(st.st_mode):
                logger.warning("Removing symlink at %s", target)
                os.unlink(target)
            elif not os.path.isdir(target):
                logger.warning("Removing non-directory at %s", target)
                os.unlink(target)
            else:
                dir_flag = getattr(os, "O_DIRECTORY", None)
                nofollow_flag = getattr(os, "O_NOFOLLOW", None)
                if dir_flag is not None and nofollow_flag is not None:
                    try:
                        fd = os.open(target, os.O_RDONLY | dir_flag | nofollow_flag)
                        os.close(fd)
                    except OSError:
                        logger.warning("Removing unsafe directory at %s", target)
                        os.unlink(target)
        except OSError:
            pass
        if not os.path.isdir(target):
            try:
                os.makedirs(target, mode=0o700, exist_ok=True)
            except OSError:
                tmp = tempfile.mkdtemp(prefix="NoWires-", dir=base)
                try:
                    os.chmod(tmp, 0o700)
                except OSError:
                    pass
                try:
                    os.rename(tmp, target)
                except OSError:
                    logger.debug("Could not rename %s to %s; using temp path", tmp, target)
                    target = tmp
        try:
            st = os.stat(target)
            if st.st_mode & 0o777 != 0o700:
                os.chmod(target, 0o700)
        except OSError:
            pass
    return target


def tile_name_for(lat, lon):
    lat, lon = math.floor(lat), math.floor(lon)
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return "Copernicus_DSM_COG_10_{}{:02d}_00_{}{:03d}_00_DEM".format(
        ns, abs(lat), ew, abs(lon)
    )


def required_tiles(south, north, west, east, feedback=None, max_tiles=_MAX_TILES):
    aoi_geom = QgsGeometry.fromRect(QgsRectangle(west, south, east, north))

    tiles = []
    for lon_west, lon_east in longitude_intervals(west, east):
        for lat in range(math.floor(south), math.ceil(north)):
            for lon in range(math.floor(lon_west), math.ceil(lon_east)):
                tile_points = [
                    QgsPointXY(lon, lat),
                    QgsPointXY(lon + 1, lat),
                    QgsPointXY(lon + 1, lat + 1),
                    QgsPointXY(lon, lat + 1),
                ]
                tile_poly = QgsGeometry.fromPolygonXY([tile_points])
                if tile_poly.intersection(aoi_geom).isEmpty():
                    continue
                name = tile_name_for(lat, lon)
                if name not in tiles:
                    tiles.append(name)
                    if feedback:
                        feedback.pushInfo("Required tile: " + name)

    if len(tiles) > max_tiles:
        raise ValueError(
            "Area requires {} tiles (max {}). "
            "Reduce the analysis area or increase the grid step.".format(
                len(tiles), max_tiles
            )
        )

    return tiles


def download_tiles(tile_list: list[str], temp_dir: str | None = None,
                   feedback: Any | None = None, proxy_opener: Any | None = None) -> list[str]:
    if temp_dir is None:
        temp_dir = get_temp_dir()

    ctx = ssl.create_default_context()
    default_opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
    available: list[str] = []

    for tile_name in tile_list:
        if feedback and feedback.isCanceled():
            return available

        local_tif = os.path.join(temp_dir, os.path.basename(tile_name) + ".tif")
        tile_url = "{}{}/{}.tif".format(COPERNICUS_BASE_URL, tile_name, tile_name)

        result = download_tile_with_retry(
            tile_url=tile_url,
            local_tif=local_tif,
            base_name_label=tile_name,
            feedback=feedback,
            max_retries=_DOWNLOAD_RETRIES,
            socket_timeout=_SOCKET_TIMEOUT,
            valid_tile_re=_VALID_TILE_RE,
            base_url=COPERNICUS_BASE_URL,
            opener=proxy_opener or default_opener,
        )
        if result is not None:
            available.append(result)

    return available


def clip_and_merge(tile_paths, south, north, west, east, temp_dir=None, feedback=None):
    if temp_dir is None:
        temp_dir = get_temp_dir()

    return clip_and_merge_tiles(
        tile_paths, south, north, west, east, temp_dir, feedback,
        nodata_value=-32768, aoi_prefix="", merge_filename="merged_dem.tif",
    )


def ensure_dem_for_area(south, north, west, east, feedback=None, proxy_opener=None):
    temp_dir = get_temp_dir()

    if feedback:
        feedback.pushInfo("Calculating required GLO-30 tiles")

    tiles = required_tiles(south, north, west, east, feedback=feedback)
    if not tiles:
        if feedback:
            feedback.pushInfo("No tiles found for the given area.")
        return None

    if feedback:
        feedback.pushInfo("Downloading DEM tiles")

    tile_paths = download_tiles(
        tiles, temp_dir=temp_dir, feedback=feedback, proxy_opener=proxy_opener
    )

    if not tile_paths:
        if feedback:
            feedback.pushInfo("No tiles were downloaded successfully.")
        return None

    if len(tile_paths) == 1:
        return tile_paths[0]

    if feedback:
        feedback.pushInfo("Clipping and merging DEM tiles")

    merge_temp_dir = tempfile.mkdtemp(prefix="nowires_dem_", dir=temp_dir)
    # temp_dir (from get_temp_dir()) is already TOCTOU-safe, so the
    # subdirectory created by mkdtemp inside it inherits that safety.
    os.chmod(merge_temp_dir, 0o700)
    if feedback:
        feedback.pushInfo(
            "Merged DEM outputs are kept in a per-run folder for QGIS layer loading: "
            + merge_temp_dir
        )

    return clip_and_merge(
        tile_paths,
        south,
        north,
        west,
        east,
        temp_dir=merge_temp_dir,
        feedback=feedback,
    )
