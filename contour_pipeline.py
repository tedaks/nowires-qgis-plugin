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


DEM tile download, clip, merge, proxy-setup and layer-loading helpers.
"""

import os
import tempfile

from osgeo import gdal, ogr

from qgis.PyQt.QtGui import QPainter
from qgis.core import QgsApplication, QgsAuthMethodConfig, QgsProject, QgsRasterLayer

from .base_algorithm import ENTRY_KEY_LAST_DEM
from .dem_downloader import required_tiles, download_tiles
from .processing_utils import queue_layer_for_loading


def setup_proxy_opener(auth_id, feedback):
    """Build a urllib proxy opener from a QGIS auth config, or return None."""
    if not auth_id:
        return None
    import urllib.request
    from urllib.parse import urlparse
    try:
        auth_mgr = QgsApplication.authManager()
        auth_cfg = QgsAuthMethodConfig()
        auth_mgr.loadAuthenticationConfig(auth_id, auth_cfg, True)
        auth_info = auth_cfg.configMap()
        proxy_host = urlparse(auth_info["realm"]).hostname
        proxy_port = urlparse(auth_info["realm"]).port
        proxy_user = auth_info["username"]
        proxy_pass = auth_info["password"]
        proxy_base_url = "http://{}:{}".format(proxy_host, proxy_port)
        proxy_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        proxy_mgr.add_password(None, proxy_base_url, proxy_user, proxy_pass)
        proxy_auth_handler = urllib.request.ProxyBasicAuthHandler(proxy_mgr)
        proxy_handler = urllib.request.ProxyHandler(
            {"http": proxy_base_url, "https": proxy_base_url}
        )
        opener = urllib.request.build_opener(proxy_handler, proxy_auth_handler)
        feedback.pushInfo("\nUsing proxy authentication")
        return opener
    except Exception as e:
        feedback.pushInfo("\nFailed to load proxy auth: " + str(type(e).__name__))
        return None


def write_aoi_shapefile(aoi_geometry, aoi_shp_path):
    """Write an OGR polygon shapefile from a QgsGeometry for clipping."""
    from .report_markers import remove_existing_ogr_dataset
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    remove_existing_ogr_dataset(shp_driver, aoi_shp_path)
    aoi_datasource = shp_driver.CreateDataSource(aoi_shp_path)
    aoi_layer = aoi_datasource.CreateLayer("layer", geom_type=ogr.wkbPolygon)
    feat_defn = aoi_layer.GetLayerDefn()
    feature = ogr.Feature(feat_defn)
    wkt = aoi_geometry.asWkt()
    ogr_geom = ogr.CreateGeometryFromWkt(wkt)
    if ogr_geom is None:
        raise RuntimeError("Failed to convert geometry to OGR format.")
    feature.SetGeometry(ogr_geom)
    aoi_layer.CreateFeature(feature)
    aoi_datasource = None


def download_and_merge_tiles(
    south, north, west, east,
    temp_dir, aoi_shp_path, proxy_opener, feedback, progress, status_total,
):
    """Download required tiles, clip to AOI, and merge into a single raster.

    Returns (merged_path, temp_files, gdal_callback, tile_count).
    """
    feedback.pushInfo("\nCalculating required GLO-30 tiles")
    tile_list = required_tiles(south, north, west, east, feedback=feedback)
    if not tile_list:
        feedback.pushInfo("\nNo tiles found for the given area.")
        return None, [], None, 0

    progress = progress + 1
    feedback.setProgress(int(progress * status_total))

    feedback.pushInfo("\nDownloading DEM tiles")
    tile_paths = download_tiles(
        tile_list, temp_dir=temp_dir, feedback=feedback, proxy_opener=proxy_opener,
    )
    if not tile_paths:
        feedback.pushInfo("\nNo tiles downloaded successfully.")
        return None, [], None, 0

    progress += len(tile_list)

    def gdal_callback(info, *args):
        feedback.setProgress(int((progress + info) * status_total))

    feedback.pushInfo("\nClipping tiles to area of interest")
    clipped_rasters = []
    temp_files = []
    for tile_path in tile_paths:
        if feedback.isCanceled():
            return None, [], None, 0
        base = os.path.splitext(os.path.basename(tile_path))[0]
        fn_clip = os.path.join(temp_dir, base + "_clip.tif")
        temp_files.append(fn_clip)
        feedback.pushInfo("Clipping: " + os.path.basename(tile_path))
        clip_result = gdal.Warp(
            fn_clip, tile_path,
            cutlineDSName=aoi_shp_path, cropToCutline=True,
            dstNodata=-32768, srcSRS="EPSG:4326", dstSRS="EPSG:4326",
            format="GTiff", callback=gdal_callback,
        )
        if clip_result is not None:
            clip_result = None
        else:
            continue
        if gdal.Open(fn_clip) is None:
            continue
        clipped_rasters.append(fn_clip)
        progress += 1
        feedback.setProgress(int(progress * status_total))

    if not clipped_rasters:
        feedback.pushInfo("\nNo DEM tiles clipped successfully.")
        return None, temp_files, gdal_callback, len(tile_list)

    feedback.pushInfo("\nMerging clipped tiles")
    merged_path = os.path.join(temp_dir, "merged_contour.tif")
    temp_files.append(merged_path)
    merge_result = gdal.Warp(
        merged_path, clipped_rasters,
        dstNodata=-32768, format="GTiff", callback=gdal_callback,
    )
    if merge_result is None:
        raise RuntimeError(
            "Failed to merge clipped DEM tiles. "
            "All tiles may be empty or invalid for the selected area."
        )
    merge_result = None
    progress += 1
    feedback.setProgress(int(progress * status_total))

    return merged_path, temp_files, gdal_callback, len(tile_list)


def load_dem_output(dem_output, elevation_dem_path, context, feedback):
    """Export raw DEM to *dem_output* and return (layer_id_or_None)."""
    translate_ds = gdal.Translate(dem_output, elevation_dem_path)
    if translate_ds is not None:
        translate_ds = None
    layer = QgsRasterLayer(dem_output, "NoWires DEM")
    if not layer.isValid():
        feedback.pushInfo("Warning: Could not load NoWires DEM layer")
        return None
    queue_layer_for_loading(context, layer, "NoWires DEM")
    QgsProject.instance().writeEntry("NoWires", ENTRY_KEY_LAST_DEM, layer.id())
    return layer.id()


def load_overlay_layer(elevation_dem_path, temp_dir, context, feedback):
    """Prepare hillshade overlay and return (layer_id_or_None, overlay_dir)."""
    feedback.pushInfo("\nAdding Elevation Overlay layer")
    overlay_dir = tempfile.mkdtemp(dir=temp_dir, prefix="contour_overlay_")
    feedback.pushInfo("Elevation overlay outputs in: " + overlay_dir)

    from .contour_overlay import prepare_elevation_overlay
    overlay_path = prepare_elevation_overlay(
        elevation_dem_path, overlay_dir, context, feedback
    )
    layer = QgsRasterLayer(overlay_path, "Elevation Overlay")
    if not layer.isValid():
        feedback.pushInfo("Warning: Could not load Elevation Overlay layer")
        return None, overlay_dir

    layer.setBlendMode(QPainter.CompositionMode.CompositionMode_ColorDodge)
    queue_layer_for_loading(context, layer, "Elevation Overlay")
    return layer.id(), overlay_dir
