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
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
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


Copernicus GLO-30 DEM tile download, caching, and merging.

Downloads Cloud-Optimized GeoTIFF tiles on demand from the public
``copernicus-dem-30m`` AWS Open Data bucket, caches them per-user, and
clips/merges them to a requested area of interest. Structurally mirrors
``worldcover_downloader.py``; the GLO-30 tile layout and naming are
documented facts (see https://copernicus-dem-30m.s3.amazonaws.com/readme.html).
This module is original work written from those public specifications and the
project's own tests (see CLEANROOM.md); see NOTICE.md for attribution.
"""

from __future__ import annotations

import getpass
import logging
import math
import os
import re
import ssl
import stat
import tempfile
import urllib.request
from typing import Any

from qgis.core import QgsGeometry, QgsPointXY, QgsRectangle

from NoWires.constants import DEM_NODATA, DIR_PERMISSIONS
from NoWires.geo_bounds import longitude_intervals
from NoWires.tile_download_base import download_tile_with_retry
from NoWires.tile_merge import clip_and_merge_tiles

logger = logging.getLogger(__name__)

COPERNICUS_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/"
_MAX_TILES = 200
_DOWNLOAD_RETRIES = 3
_SOCKET_TIMEOUT = 60
_VALID_TILE_RE = re.compile(r"^Copernicus_DSM_COG_10_[NS]\d{2}_00_[EW]\d{3}_00_DEM$")
# Rough per-tile footprint used only for the pre-download AOI summary.
_EST_MB_PER_TILE = 25


def _ensure_dir(target):
    """Create *target* as a directory safely, avoiding symlink TOCTOU races.

    Uses os.lstat + O_DIRECTORY|O_NOFOLLOW validation for an existing entry and
    an atomic tempfile.mkdtemp + os.rename when creating. Falls back to the
    temporary path if the rename cannot complete.
    """
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
        parent = os.path.dirname(target)
        tmp = tempfile.mkdtemp(dir=parent)
        try:
            os.chmod(tmp, DIR_PERMISSIONS)
        except OSError:
            pass
        try:
            os.rename(tmp, target)
        except OSError:
            logger.debug("Could not rename %s to %s; using temp path", tmp, target)
            return tmp
    try:
        if os.stat(target).st_mode & 0o777 != DIR_PERMISSIONS:
            os.chmod(target, DIR_PERMISSIONS)
    except OSError:
        pass
    return target


def get_temp_dir(create=True):
    """Return the per-user DEM cache directory (``<tmp>/NoWires-<user>``)."""
    try:
        username = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser())
    except (OSError, KeyError):
        username = "nowires"
    target = os.path.join(tempfile.gettempdir(), "NoWires-" + username)
    if not create:
        return target
    return _ensure_dir(target)


def tile_name_for(lat, lon):
    """Return the GLO-30 tile base name for the 1x1 degree cell containing lat/lon."""
    lat_i = math.floor(lat)
    lon_i = math.floor(lon)
    ns = "N" if lat_i >= 0 else "S"
    ew = "E" if lon_i >= 0 else "W"
    return "Copernicus_DSM_COG_10_{}{:02d}_00_{}{:03d}_00_DEM".format(
        ns, abs(lat_i), ew, abs(lon_i))


def required_tiles(south, north, west, east, feedback=None, max_tiles=_MAX_TILES):
    """Enumerate the GLO-30 tiles whose 1-degree cell overlaps the bounding box."""
    tiles: list[str] = []
    for lon_west, lon_east in longitude_intervals(west, east):
        aoi = QgsGeometry.fromRect(QgsRectangle(lon_west, south, lon_east, north))
        for lat in range(math.floor(south), math.ceil(north)):
            for lon in range(math.floor(lon_west), math.ceil(lon_east)):
                tile = QgsGeometry.fromPolygonXY([[
                    QgsPointXY(lon, lat), QgsPointXY(lon + 1, lat),
                    QgsPointXY(lon + 1, lat + 1), QgsPointXY(lon, lat + 1),
                ]])
                if not tile.intersection(aoi).isEmpty():
                    name = tile_name_for(lat, lon)
                    if name not in tiles:
                        tiles.append(name)
    if len(tiles) > max_tiles:
        raise ValueError(
            "Area requires {} DEM tiles (max {}). "
            "Reduce the analysis area.".format(len(tiles), max_tiles)
        )
    return tiles


def download_tiles(tile_list: list[str], temp_dir: str | None = None,
                   feedback: Any | None = None, proxy_opener: Any | None = None) -> list[str]:
    """Download each GLO-30 tile into *temp_dir*; return the local paths obtained."""
    if temp_dir is None:
        temp_dir = get_temp_dir()

    opener = proxy_opener
    if opener is None:
        ctx = ssl.create_default_context()
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

    available: list[str] = []
    for tile_name in tile_list:
        if feedback and feedback.isCanceled():
            return available
        local_tif = os.path.join(temp_dir, tile_name + ".tif")
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
            opener=opener,
        )
        if result is not None:
            available.append(result)

    return available


def clip_and_merge(tile_paths, south, north, west, east, temp_dir=None, feedback=None):
    """Clip the tiles to the AOI and merge them into a single GeoTIFF."""
    if temp_dir is None:
        temp_dir = get_temp_dir()
    return clip_and_merge_tiles(
        tile_paths, south, north, west, east, temp_dir, feedback,
        nodata_value=DEM_NODATA, aoi_prefix="dem", merge_filename="merged_dem.tif",
    )


def ensure_dem_for_area(south, north, west, east, feedback=None, proxy_opener=None):
    """Download, clip, and merge the GLO-30 DEM covering the bounding box.

    Returns the path to a single-tile cache file or the merged clip, or None
    when no tile covers the area or every download fails.
    """
    temp_dir = get_temp_dir()

    if feedback:
        feedback.pushInfo("Calculating required GLO-30 tiles")

    tiles = required_tiles(south, north, west, east, feedback=feedback)
    if not tiles:
        if feedback:
            feedback.pushInfo("No tiles found for the given area.")
        return None

    if feedback:
        lat_span = abs(north - south)
        lon_span = abs(east - west)
        feedback.pushInfo(
            "AOI {:.2f}°×{:.2f}°: {} GLO-30 tile(s), "
            "~{} MB, ~{} Mpx".format(
                lon_span, lat_span, len(tiles),
                len(tiles) * _EST_MB_PER_TILE,
                round(len(tiles) * 3600 * 3600 / 1_000_000),
            )
        )
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
    os.chmod(merge_temp_dir, DIR_PERMISSIONS)
    if feedback:
        feedback.pushInfo(
            "Merged DEM outputs are kept in a per-run folder: " + merge_temp_dir
        )

    return clip_and_merge(
        tile_paths, south, north, west, east, temp_dir=merge_temp_dir, feedback=feedback
    )
