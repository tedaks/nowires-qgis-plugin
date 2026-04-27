# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Daniel Hulshof Saint Martin
                               Adaptations (C) 2026 by Bortre Tenamo
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

import logging
import math
import os
import re
import ssl
import tempfile
import time
import urllib.error
import urllib.request

from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
)

logger = logging.getLogger(__name__)

COPERNICUS_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/"
_MAX_TILES = 200
_DOWNLOAD_RETRIES = 3
_VALID_TILE_RE = re.compile(r"^Copernicus_DSM_COG_10_[NS]\d{2}_00_[EW]\d{3}_00_DEM$")


def get_temp_dir():
    temp_dir = os.path.join(tempfile.gettempdir(), "NoWires")
    os.makedirs(temp_dir, mode=0o700, exist_ok=True)
    return temp_dir


def tile_name_for(lat, lon):
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return "Copernicus_DSM_COG_10_{}{:02d}_00_{}{:03d}_00_DEM".format(
        ns, abs(lat), ew, abs(lon)
    )


def required_tiles(south, north, west, east, feedback=None, max_tiles=_MAX_TILES):
    aoi_geom = QgsGeometry.fromRect(QgsRectangle(west, south, east, north))

    tiles = []
    for lat in range(math.floor(south), math.ceil(north)):
        for lon in range(math.floor(west), math.ceil(east)):
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


def download_tiles(tile_list, temp_dir=None, feedback=None, proxy_opener=None):
    # NOTE: This function is NOT safe for concurrent invocation from multiple
    # threads or processes. The os.path.exists() cache check (TOCTOU race)
    # could result in two threads downloading the same tile simultaneously.
    # Since QGIS Processing algorithms use FlagNoThreading, this is acceptable
    # for the current single-threaded usage pattern.
    if temp_dir is None:
        temp_dir = get_temp_dir()

    ctx = ssl.create_default_context()
    default_opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
    available = []

    for tile_name in tile_list:
        if feedback and feedback.isCanceled():
            return available

        if not _VALID_TILE_RE.match(tile_name):
            logger.error("Invalid tile name rejected: %s", tile_name)
            continue

        local_tif = os.path.join(temp_dir, tile_name + ".tif")

        if os.path.exists(local_tif):
            logger.debug("Cache hit: %s", tile_name)
            if feedback:
                feedback.pushInfo("Cache hit: " + tile_name)
            available.append(local_tif)
            continue

        tile_url = "{}{}/{}.tif".format(COPERNICUS_BASE_URL, tile_name, tile_name)
        if feedback:
            feedback.pushInfo("Downloading: " + tile_url)

        opener = proxy_opener or default_opener
        downloaded = False

        for attempt in range(_DOWNLOAD_RETRIES):
            if feedback and feedback.isCanceled():
                return available
            try:
                with opener.open(tile_url, timeout=60) as response:
                    final_url = response.geturl()
                    if not final_url.startswith(COPERNICUS_BASE_URL):
                        raise RuntimeError("Unexpected redirect to: " + final_url)
                    expected_size = int(response.headers.get("Content-Length", 0))
                    bytes_received = 0
                    tmp_path = local_tif + ".tmp"
                    with open(tmp_path, "wb") as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            bytes_received += len(chunk)

                if expected_size > 0 and bytes_received != expected_size:
                    logger.warning(
                        "Incomplete download %s: %d/%d bytes",
                        tile_name,
                        bytes_received,
                        expected_size,
                    )
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    if attempt < _DOWNLOAD_RETRIES - 1:
                        time.sleep(2**attempt)
                        continue
                    raise ValueError(
                        "Incomplete download: {} of {} bytes".format(
                            bytes_received, expected_size
                        )
                    )

                test_ds = gdal.Open(tmp_path)
                if test_ds is None:
                    logger.warning("Downloaded tile is corrupt: %s", tile_name)
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    if attempt < _DOWNLOAD_RETRIES - 1:
                        time.sleep(2**attempt)
                        continue
                test_ds = None

                os.rename(tmp_path, local_tif)
                available.append(local_tif)
                downloaded = True
                break

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.info("Tile not available (404): %s", tile_name)
                    if feedback:
                        feedback.pushInfo("Tile not available (HTTP 404): " + tile_name)
                    break
                else:
                    logger.warning(
                        "HTTP %d downloading %s (attempt %d/%d): %s",
                        e.code,
                        tile_name,
                        attempt + 1,
                        _DOWNLOAD_RETRIES,
                        e,
                    )
                    if attempt < _DOWNLOAD_RETRIES - 1:
                        time.sleep(2**attempt)
            except Exception as e:
                logger.warning(
                    "Error downloading %s (attempt %d/%d): %s",
                    tile_name,
                    attempt + 1,
                    _DOWNLOAD_RETRIES,
                    e,
                )
                if feedback:
                    feedback.pushInfo(
                        "Error downloading {} (attempt {}): {}".format(
                            tile_name, attempt + 1, str(e)
                        )
                    )
                if attempt < _DOWNLOAD_RETRIES - 1:
                    time.sleep(2**attempt)

        if not downloaded and os.path.exists(local_tif + ".tmp"):
            try:
                os.unlink(local_tif + ".tmp")
            except OSError:
                pass

    return available


def clip_and_merge(tile_paths, south, north, west, east, temp_dir=None, feedback=None):
    if temp_dir is None:
        temp_dir = get_temp_dir()

    if not tile_paths:
        return None

    aoi_shp = os.path.join(temp_dir, "aoi_clip.shp")
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(aoi_shp):
        shp_driver.DeleteDataSource(aoi_shp)

    ds = shp_driver.CreateDataSource(aoi_shp)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("aoi", srs=srs, geom_type=ogr.wkbPolygon)
    feat_defn = layer.GetLayerDefn()
    feature = ogr.Feature(feat_defn)

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(west, south)
    ring.AddPoint(east, south)
    ring.AddPoint(east, north)
    ring.AddPoint(west, north)
    ring.AddPoint(west, south)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    feature.SetGeometry(poly)
    layer.CreateFeature(feature)
    ds = None

    clipped = []
    for path in tile_paths:
        if feedback and feedback.isCanceled():
            return None
        base = os.path.splitext(os.path.basename(path))[0]
        clip_path = os.path.join(temp_dir, base + "_clip.tif")

        if feedback:
            feedback.pushInfo("Clipping: " + os.path.basename(path))

        result = gdal.Warp(
            clip_path,
            path,
            cutlineDSName=aoi_shp,
            cropToCutline=True,
            dstNodata=-32768,
            srcSRS="EPSG:4326",
            dstSRS="EPSG:4326",
            format="GTiff",
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        if result is None:
            logger.warning("Warp failed for %s", os.path.basename(path))
            continue
        result = None

        check = gdal.Open(clip_path)
        if check is None:
            logger.warning("Empty clip result for %s", os.path.basename(path))
            continue
        check = None
        clipped.append(clip_path)

    if not clipped:
        return None

    merged_path = os.path.join(temp_dir, "merged_dem.tif")
    if feedback:
        feedback.pushInfo("Merging {} clipped tiles".format(len(clipped)))

    result = gdal.Warp(
        merged_path,
        clipped,
        dstNodata=-32768,
        format="GTiff",
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )
    if result is None:
        logger.error("Merge Warp failed")
        return None
    result = None

    return merged_path


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

    return clip_and_merge(
        tile_paths,
        south,
        north,
        west,
        east,
        temp_dir=temp_dir,
        feedback=feedback,
    )
