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


Shared tile download logic with retry, validation, and caching for DEM and WorldCover downloaders.
"""

import logging
import os
import time
import urllib.error

from osgeo import gdal, ogr, osr

from .geo_bounds import longitude_intervals

logger = logging.getLogger(__name__)
DEFAULT_PER_TILE_WALL_CLOCK_BUDGET = 180  # caps slow trickles where socket_timeout never fires


def download_tile_with_retry(
    tile_url, local_tif, base_name_label, feedback=None,
    max_retries=3, socket_timeout=60, valid_tile_re=None,
    base_url=None, opener=None,
    wall_clock_budget=DEFAULT_PER_TILE_WALL_CLOCK_BUDGET,
):
    if valid_tile_re is not None and not valid_tile_re.match(base_name_label):
        logger.error("Invalid tile name rejected: %s", base_name_label)
        return None

    if os.path.exists(local_tif):
        test_ds = gdal.Open(local_tif)
        if test_ds is not None:
            try:
                band_count = test_ds.RasterCount
                xsize = test_ds.RasterXSize
                ysize = test_ds.RasterYSize
                if xsize > 0 and ysize > 0 and band_count >= 1:
                    logger.debug("Cache hit: %s (%dx%d)", base_name_label, xsize, ysize)
                    if feedback:
                        feedback.pushInfo("Cache hit: " + base_name_label)
                    return local_tif
                logger.warning(
                    "Cached tile %s has degenerate dimensions; re-downloading",
                    base_name_label)
            finally:
                test_ds = None
        else:
            logger.warning("Cached tile %s failed validation; re-downloading", base_name_label)
        try:
            os.unlink(local_tif)
        except OSError:
            pass

    if feedback:
        feedback.pushInfo("Downloading: " + tile_url)
    downloaded = False
    tmp_path = local_tif + ".tmp"
    t_start = time.monotonic()
    for attempt in range(max_retries):
        if feedback and feedback.isCanceled():
            return None
        elapsed = time.monotonic() - t_start
        if wall_clock_budget is not None and elapsed >= wall_clock_budget:
            logger.warning("Wall-clock budget exceeded (%.1f/%.1f s) for %s",
                           elapsed, wall_clock_budget, base_name_label)
            if feedback:
                feedback.pushInfo("Download budget exceeded: " + base_name_label)
            break
        try:
            with opener.open(tile_url, timeout=socket_timeout) as response:
                final_url = response.geturl()
                if base_url is not None:
                    from urllib.parse import urlsplit
                    if urlsplit(final_url).netloc.lower() != urlsplit(base_url).netloc.lower():
                        raise RuntimeError("Unexpected redirect to: " + final_url)
                content_length_hdr = response.headers.get("Content-Length")
                if content_length_hdr is None:
                    logger.debug("No Content-Length header for %s", base_name_label)
                    expected_size = 0
                else:
                    expected_size = int(content_length_hdr)
                bytes_received = 0
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)
                    f.flush()
                    os.fsync(f.fileno())

            if expected_size > 0 and bytes_received != expected_size:
                logger.warning(
                    "Incomplete download %s: %d/%d bytes",
                    base_name_label,
                    bytes_received,
                    expected_size,
                )
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise ValueError(
                    "Incomplete download: {} of {} bytes".format(
                        bytes_received, expected_size
                    )
                )

            test_ds = gdal.Open(tmp_path)
            if test_ds is None:
                logger.warning("Downloaded tile is corrupt: %s", base_name_label)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                break
            test_ds = None  # Release GDAL dataset handle promptly
            os.replace(tmp_path, local_tif)
            downloaded = True
            break

        except urllib.error.HTTPError as e:
            retryable_codes = {408, 425, 429}
            if e.code == 404:
                logger.info("Tile not available (404): %s", base_name_label)
                if feedback:
                    feedback.pushInfo("Tile not available (HTTP 404): " + base_name_label)
                break
            elif e.code in retryable_codes or e.code >= 500:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_secs = max(int(retry_after), 1)
                    except ValueError:
                        wait_secs = 2 ** attempt
                else:
                    wait_secs = 2 ** attempt
                msg = "HTTP {} on {} (attempt {}/{}); retry in {}s".format(
                    e.code, base_name_label, attempt + 1, max_retries, wait_secs)
                logger.warning(msg)
                if feedback:
                    feedback.pushInfo(msg)
                if attempt < max_retries - 1:
                    time.sleep(wait_secs)
            else:
                msg = "HTTP {} on {} (non-retryable)".format(e.code, base_name_label)
                logger.error(msg)
                if feedback:
                    feedback.pushWarning(msg)
                break
        except Exception as e:
            logger.warning("Error downloading %s (attempt %d/%d): %s",
                base_name_label, attempt + 1, max_retries, e)
            if feedback:
                feedback.pushInfo("Error downloading {} (attempt {}): {}".format(
                    base_name_label, attempt + 1, str(e)))
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    if not downloaded and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return local_tif if downloaded else None


def _rectangle_geometry(south, north, west, east, ogr_module=ogr):
    ring = ogr_module.Geometry(ogr_module.wkbLinearRing)
    ring.AddPoint(west, south)
    ring.AddPoint(east, south)
    ring.AddPoint(east, north)
    ring.AddPoint(west, north)
    ring.AddPoint(west, south)
    poly = ogr_module.Geometry(ogr_module.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def _aoi_geometry_for_bounds(south, north, west, east, ogr_module=ogr):
    intervals = longitude_intervals(west, east)
    if len(intervals) == 1:
        return _rectangle_geometry(south, north, intervals[0][0], intervals[0][1], ogr_module)
    geom = ogr_module.Geometry(ogr_module.wkbMultiPolygon)
    for lon_west, lon_east in intervals:
        geom.AddGeometry(_rectangle_geometry(south, north, lon_west, lon_east, ogr_module))
    return geom


def clip_and_merge_tiles(
    tile_paths, south, north, west, east, temp_dir, feedback,
    nodata_value, aoi_prefix, merge_filename,
):
    if not tile_paths:
        return None

    aoi_shp = os.path.join(temp_dir, aoi_prefix + "_aoi_clip.shp")
    from .report_markers import remove_existing_ogr_dataset
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    remove_existing_ogr_dataset(shp_driver, aoi_shp)
    ds = shp_driver.CreateDataSource(aoi_shp)
    if ds is None:
        raise RuntimeError("Failed to create dataset at {}".format(aoi_shp))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("aoi", srs=srs, geom_type=ogr.wkbPolygon)
    feat_defn = layer.GetLayerDefn()
    feature = ogr.Feature(feat_defn)
    feature.SetGeometry(_aoi_geometry_for_bounds(south, north, west, east))
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
            dstNodata=nodata_value,
            srcSRS="EPSG:4326",
            dstSRS="EPSG:4326",
            format="GTiff",
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        if result is None:
            logger.warning("Warp failed for %s", os.path.basename(path))
            continue
        result = None  # Release GDAL dataset handle promptly

        check = gdal.Open(clip_path)
        if check is None:
            logger.warning("Empty clip result for %s", os.path.basename(path))
            continue
        check = None
        clipped.append(clip_path)

    if not clipped:
        return None

    merged_path = os.path.join(temp_dir, merge_filename)
    if feedback:
        feedback.pushInfo("Merging {} clipped tiles".format(len(clipped)))
    result = gdal.Warp(
        merged_path, clipped, dstNodata=nodata_value, format="GTiff",
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )
    if result is None:
        logger.error("Merge Warp failed")
        return None
    result = None  # Release GDAL dataset handle promptly
    return merged_path
