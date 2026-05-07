# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
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

import logging
import math
import os
import re
import stat
import ssl
import time
import tempfile
import urllib.request
import getpass



from .geo_bounds import longitude_intervals
from .tile_download_base import clip_and_merge_tiles, download_tile_with_retry

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
_WALL_CLOCK_TIMEOUT = 600


def _safe_create_dir(target):
    """Create or validate a directory safely, avoiding symlink TOCTOU races.

    Uses tempfile.mkdtemp() for atomic creation when the directory does not
    yet exist. On platforms that support O_DIRECTORY | O_NOFOLLOW, also uses
    os.open to verify an existing directory is not a symlink.
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
            os.chmod(tmp, 0o700)
        except OSError:
            pass
        try:
            os.rename(tmp, target)
        except OSError:
            logger.debug("Could not rename %s to %s; using temp path", tmp, target)
            return tmp
    try:
        st = os.stat(target)
        if st.st_mode & 0o777 != 0o700:
            os.chmod(target, 0o700)
    except OSError:
        pass
    return target


def get_worldcover_dir():
    try:
        username = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser())
    except (OSError, KeyError):
        username = "nowires"
    base = tempfile.gettempdir()
    nowires_dir = os.path.join(base, "NoWires-" + username)
    nowires_dir = _safe_create_dir(nowires_dir)
    target = os.path.join(nowires_dir, "worldcover")
    return _safe_create_dir(target)


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


def download_worldcover_tiles(tile_list, temp_dir=None, feedback=None):
    if temp_dir is None:
        temp_dir = get_worldcover_dir()

    ctx = ssl.create_default_context()
    default_opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
    available = []
    deadline = time.monotonic() + _WALL_CLOCK_TIMEOUT

    for tile_id in tile_list:
        if feedback and feedback.isCanceled():
            return available
        if time.monotonic() > deadline:
            logger.warning("WorldCover download wall-clock timeout exceeded (%ds)", _WALL_CLOCK_TIMEOUT)
            if feedback:
                feedback.pushInfo(
                    "Download timed out after {}s".format(_WALL_CLOCK_TIMEOUT))
            break

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
