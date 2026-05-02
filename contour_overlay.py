# -*- coding: utf-8 -*-
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


Hillshade overlay raster preparation for contour display.
"""

import os

from osgeo import gdal

from .overlay_raster import build_overview_levels, choose_overlay_dimensions


def prepare_elevation_overlay(source_dem_path, persistent_temp_dir, context, feedback):
    """Build a lighter hillshade raster so the overlay draws quickly in QGIS.

    Returns the path to the generated hillshade GeoTIFF.
    """
    feedback.pushInfo("Optimizing overlay raster for display...")

    source_ds = gdal.Open(source_dem_path)
    if source_ds is None:
        raise RuntimeError("Could not open overlay DEM: " + source_dem_path)

    src_width = source_ds.RasterXSize
    src_height = source_ds.RasterYSize
    source_ds = None

    overlay_width, overlay_height, scale = choose_overlay_dimensions(src_width, src_height)
    overlay_dem_path = os.path.join(persistent_temp_dir, "elevation_overlay_dem.tif")
    overlay_hillshade_path = os.path.join(persistent_temp_dir, "elevation_overlay_hillshade.tif")

    project_crs = context.project().crs()
    dst_srs = "EPSG:4326"
    if project_crs.isValid():
        dst_srs = project_crs.authid()

    if scale < 1.0:
        feedback.pushInfo(
            "Downsampling overlay raster from {}x{} to {}x{} for faster display.".format(
                src_width, src_height, overlay_width, overlay_height
            )
        )

    translate_result = gdal.Warp(
        overlay_dem_path,
        source_dem_path,
        format="GTiff",
        dstNodata=-32768,
        dstSRS=dst_srs,
        width=overlay_width,
        height=overlay_height,
        resampleAlg=gdal.GRA_Bilinear,
        multithread=True,
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"],
    )
    if translate_result is None:
        raise RuntimeError("Failed to prepare optimized overlay raster.")
    translate_result = None

    hillshade_result = gdal.DEMProcessing(
        overlay_hillshade_path,
        overlay_dem_path,
        "hillshade",
        format="GTiff",
        azimuth=315,
        altitude=45,
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"],
    )
    if hillshade_result is None:
        raise RuntimeError("Failed to generate optimized hillshade overlay.")
    hillshade_result = None

    overview_levels = build_overview_levels(overlay_width, overlay_height)
    if overview_levels:
        feedback.pushInfo(
            "Building overlay pyramids: {}".format(
                ", ".join(str(level) for level in overview_levels)
            )
        )
        hillshade_ds = gdal.Open(overlay_hillshade_path, gdal.GA_Update)
        if hillshade_ds is not None:
            hillshade_ds.BuildOverviews("AVERAGE", overview_levels)
            hillshade_ds = None

    return overlay_hillshade_path