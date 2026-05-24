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


ESA WorldCover 2020 v100 tile download, caching, and merging.

Downloads Cloud-Optimized GeoTIFF tiles from the ESA WorldCover AWS
Open Data bucket on demand, caches them locally, and provides
utilities to clip/merge for a given area of interest.

ESA WorldCover 2020 data is provided under the ESA WorldCover licence.
See NOTICE.md for full attribution and licence details.
"""

from __future__ import annotations

import logging
import math
import os
import re
import ssl
import tempfile
import urllib.request
import getpass
from typing import Any



from NoWires.fs_utils import safe_create_dir
from NoWires.constants import DIR_PERMISSIONS
from NoWires.geo_bounds import longitude_intervals
from NoWires.tile_download_base import clip_and_merge_tiles, download_tile_with_retry

logger = logging.getLogger(__name__)

WORLDCOVER_BASE_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
    "/v100/2020/map/"
)
WORLDCOVER_TILE_SIZE_DEG = 3
_DOWNLOAD_RETRIES = 3
_SOCKET_TIMEOUT = 120
_MAX_TILES = 200
_VALID_TILE_RE = re.compile(r"^[NS]\d{2}[EW]\d{3}$")


def get_worldcover_dir():
    try:
        username = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser())
    except (OSError, KeyError):
        username = "nowires"
    base = tempfile.gettempdir()
    nowires_dir = os.path.join(base, "NoWires-" + username)
    nowires_dir = safe_create_dir(nowires_dir)
    target = os.path.join(nowires_dir, "worldcover")
    return safe_create_dir(target)


def worldcover_tile_id(lat, lon):
    snapped_lat = math.floor(lat / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG
    snapped_lon = math.floor(lon / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG
    ns = "N" if snapped_lat >= 0 else "S"
    ew = "E" if snapped_lon >= 0 else "W"
    return "{}{:02d}{}{:03d}".format(ns, abs(snapped_lat), ew, abs(snapped_lon))


def worldcover_tile_filename(tile_id):
    return "ESA_WorldCover_10m_2020_v100_{}_Map.tif".format(tile_id)


def worldcover_tile_url(tile_id):
    return "{}{}".format(WORLDCOVER_BASE_URL, worldcover_tile_filename(tile_id))


def required_worldcover_tiles(south, north, west, east, max_tiles=_MAX_TILES):
    tiles = []
    for lon_west, lon_east in longitude_intervals(west, east):
        for lat in range(
            math.floor(south / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
            math.ceil(north / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
            WORLDCOVER_TILE_SIZE_DEG,
        ):
            for lon in range(
                math.floor(lon_west / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
                math.ceil(lon_east / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
                WORLDCOVER_TILE_SIZE_DEG,
            ):
                tile_id = worldcover_tile_id(lat, lon)
                if tile_id not in tiles:
                    tiles.append(tile_id)

    if len(tiles) > max_tiles:
        raise ValueError(
            "Area requires {} WorldCover tiles (max {}). "
            "Reduce the analysis area.".format(len(tiles), max_tiles)
        )
    return tiles


def download_worldcover_tiles(tile_list: list[str], temp_dir: str | None = None,
                             feedback: Any | None = None) -> list[str]:
    if temp_dir is None:
        temp_dir = get_worldcover_dir()

    ctx = ssl.create_default_context()
    default_opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
    available: list[str] = []

    for tile_id in tile_list:
        if feedback and feedback.isCanceled():
            return available

        filename = worldcover_tile_filename(tile_id)
        local_tif = os.path.join(temp_dir, filename)
        tile_url = worldcover_tile_url(tile_id)

        result = download_tile_with_retry(
            tile_url=tile_url,
            local_tif=local_tif,
            base_name_label=tile_id,
            feedback=feedback,
            max_retries=_DOWNLOAD_RETRIES,
            socket_timeout=_SOCKET_TIMEOUT,
            valid_tile_re=_VALID_TILE_RE,
            base_url=WORLDCOVER_BASE_URL,
            opener=default_opener,
        )
        if result is not None:
            available.append(result)

    return available


def clip_and_merge_worldcover(tile_paths, south, north, west, east, temp_dir=None, feedback=None):
    if temp_dir is None:
        temp_dir = get_worldcover_dir()

    return clip_and_merge_tiles(
        tile_paths, south, north, west, east, temp_dir, feedback,
        nodata_value=0, aoi_prefix="worldcover", merge_filename="merged_worldcover.tif",
    )


def ensure_worldcover_for_area(south, north, west, east, feedback=None):
    temp_dir = get_worldcover_dir()

    if feedback:
        feedback.pushInfo("Calculating required WorldCover tiles")

    tiles = required_worldcover_tiles(south, north, west, east)
    if not tiles:
        if feedback:
            feedback.pushInfo("No WorldCover tiles found for the given area.")
        return None

    if feedback:
        feedback.pushInfo("Downloading WorldCover tiles")

    tile_paths = download_worldcover_tiles(
        tiles, temp_dir=temp_dir, feedback=feedback
    )

    if not tile_paths:
        if feedback:
            feedback.pushInfo("No WorldCover tiles were downloaded successfully.")
        return None

    if len(tile_paths) == 1:
        return tile_paths[0]

    if feedback:
        feedback.pushInfo("Clipping and merging WorldCover tiles")

    merge_temp_dir = tempfile.mkdtemp(prefix="nowires_worldcover_", dir=temp_dir)
    os.chmod(merge_temp_dir, DIR_PERMISSIONS)
    if feedback:
        feedback.pushInfo(
            "Merged WorldCover outputs are kept in a per-run folder: "
            + merge_temp_dir
        )

    return clip_and_merge_worldcover(
        tile_paths,
        south,
        north,
        west,
        east,
        temp_dir=merge_temp_dir,
        feedback=feedback,
    )
