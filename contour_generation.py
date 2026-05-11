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


Contour line generation from DEM raster and reprojection to project CRS.
"""

import os
import tempfile

from osgeo import gdal, ogr, osr


def generate_contour_lines(merged_path, interval, temp_dir, gdal_callback):
    """Generate contour shapefile from DEM raster using gdal.ContourGenerate.

    Returns (contour_shp_path, temp_shp_dir).
    """
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    tmp_shp_dir = tempfile.mkdtemp(dir=temp_dir, prefix="contourlines_")
    contour_shp_path = os.path.join(tmp_shp_dir, "contourlines.shp")
    shp_ds = shp_driver.CreateDataSource(contour_shp_path)
    srs_4326 = osr.SpatialReference()
    srs_4326.ImportFromEPSG(4326)
    srs_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    contour_layer = shp_ds.CreateLayer("Contour Lines", srs=srs_4326)
    contour_layer.CreateField(ogr.FieldDefn("ID", ogr.OFTInteger))
    contour_layer.CreateField(ogr.FieldDefn("ELEV", ogr.OFTReal))
    merged_ds = gdal.Open(merged_path)
    if merged_ds is None:
        shp_ds = None
        raise RuntimeError("Cannot open merged DEM for contour generation: {}".format(merged_path))
    try:
        merged_band = merged_ds.GetRasterBand(1)
        nodata_val = merged_band.GetNoDataValue()
        gdal.ContourGenerate(
            merged_band, interval, 0, [],
            1 if nodata_val is not None else 0,
            nodata_val if nodata_val is not None else -32768,
            contour_layer, 0, 1, callback=gdal_callback,
        )
    finally:
        shp_ds = None
        merged_ds = None
    return contour_shp_path, tmp_shp_dir


def reproject_and_export(contour_shp_path, project_crs, output_dest, temp_dir):
    """Reproject contour shapefile to project CRS if needed, then export to GPKG.

    Returns (final_output_path, reproj_temp_dir_or_None).
    """
    reproj_dir = None
    if project_crs.isValid() and project_crs.authid().upper() != "EPSG:4326":
        reproj_dir = tempfile.mkdtemp(dir=temp_dir, prefix="contourlines_reproj_")
        reproj_shp = os.path.join(reproj_dir, "contourlines_reproj.shp")
        result = gdal.VectorTranslate(
            reproj_shp, contour_shp_path,
            options=gdal.VectorTranslateOptions(
                dstSRS=project_crs.authid(), reproject=True
            ),
        )
        if result is None:
            raise RuntimeError(
                "Failed to reproject contour lines to {}".format(
                    project_crs.authid()))
        result = None
        final_shp_path = reproj_shp
    else:
        final_shp_path = contour_shp_path

    if not output_dest:
        raise RuntimeError("No contour output destination was provided.")
    result = gdal.VectorTranslate(output_dest, final_shp_path)
    if result is None:
        raise RuntimeError("Failed to export contour lines to {}".format(output_dest))
    result = None
    return output_dest, reproj_dir