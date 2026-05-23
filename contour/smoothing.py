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

Gaussian-weighted contour line smoothing guided by TPI.
"""

import logging
import os

import numpy as np
from osgeo import gdal

from NoWires.contour._smoothing_vrt import _gaussian_kernel_2d, _make_blur_vrt, _raster_calc  # noqa: F401
from NoWires.constants import DEM_NODATA

SMOOTHING_NONE = "None"
SMOOTHING_LOW = "Low"
SMOOTHING_MEDIUM = "Medium"
SMOOTHING_HIGH = "High"
SMOOTHING_OPTIONS = [SMOOTHING_NONE, SMOOTHING_LOW, SMOOTHING_MEDIUM, SMOOTHING_HIGH]

logger = logging.getLogger(__name__)

def smooth_contour_dem(smoothing, input_dem, temp_dir, feedback, progress, status_total,
                       tmp_manager=None):
    """Apply Gaussian-weighted contour line smoothing guided by TPI.

    Modifies the ``merged_contour.tif`` in *temp_dir* in-place.
    If *tmp_manager* is provided, intermediate files are registered with it
    for automatic cleanup. Otherwise files are removed on return.
    """
    if smoothing == SMOOTHING_NONE:
        return

    feedback.pushInfo("\nApplying contour line smoothing: " + smoothing)
    path = temp_dir
    temp_files = [
        os.path.join(path, "dem.tif"),
        os.path.join(path, "dem_blur_3x3.vrt"),
        os.path.join(path, "dem_tpi.tif"),
        os.path.join(path, "tpi_pos.tif"),
        os.path.join(path, "tpi_blur_3x3.vrt"),
        os.path.join(path, "tpi_norm.tif"),
    ]

    dem_tif = os.path.join(path, "dem.tif")
    src_ds_check = gdal.Open(input_dem)
    if src_ds_check is None:
        raise RuntimeError("Cannot open input DEM for smoothing: " + input_dem)
    src_nd = src_ds_check.GetRasterBand(1).GetNoDataValue()
    src_ds_check = None
    if src_nd is not None and src_nd != DEM_NODATA:
        translate_ds = gdal.Warp(
            dem_tif, input_dem, format='GTiff', outputType=gdal.GDT_Float32,
            dstNodata=DEM_NODATA, srcNodata=src_nd, creationOptions=['COMPRESS=LZW'])
    else:
        translate_ds = gdal.Translate(
            dem_tif, input_dem, outputType=gdal.GDT_Float32, noData=DEM_NODATA)
    if translate_ds is not None:
        translate_ds = None

    _make_blur_vrt(os.path.join(path, "dem_blur_3x3.vrt"), dem_tif, kernel_size=3)
    feedback.setProgress(int((progress + 0.2) * status_total))

    tpi_ds = gdal.DEMProcessing(
        destName=os.path.join(path, "dem_tpi.tif"),
        srcDS=input_dem,
        processing="TPI",
    )
    if tpi_ds is not None:
        tpi_ds = None
    _raster_calc(
        lambda A: np.abs(A),
        output_path=os.path.join(path, "tpi_pos.tif"),
        nodata=DEM_NODATA,
        overwrite=True,
        A=os.path.join(path, "dem_tpi.tif"),
    )
    feedback.setProgress(int((progress + 0.4) * status_total))

    _make_blur_vrt(
        os.path.join(path, "tpi_blur_3x3.vrt"),
        os.path.join(path, "tpi_pos.tif"),
        kernel_size=9,
    )
    feedback.setProgress(int((progress + 0.6) * status_total))

    vrt_path = os.path.join(path, "tpi_blur_3x3.vrt")
    if not os.path.exists(vrt_path):
        raise FileNotFoundError("File not found: " + vrt_path)
    vrt_ds = gdal.Open(vrt_path)
    max_val = None
    if vrt_ds is not None:
        stats = vrt_ds.GetRasterBand(1).GetStatistics(True, True)
        if stats and stats[1] is not None and stats[1] != 0:
            max_val = stats[1]
        vrt_ds = None
    try:
        if max_val is not None and max_val != 0:
            _raster_calc(
                lambda A: A / max_val,
                output_path=os.path.join(path, "tpi_norm.tif"),
                nodata=DEM_NODATA,
                overwrite=True,
                A=vrt_path,
            )
        else:
            logger.warning("Could not get TPI statistics, using raw TPI")
            fb_ds = gdal.Translate(
                destName=os.path.join(path, "tpi_norm.tif"), srcDS=vrt_path
            )
            if fb_ds is not None:
                fb_ds = None
    except Exception:
        logger.warning("TPI normalisation failed, using raw TPI")
        fb_ds = gdal.Translate(
            destName=os.path.join(path, "tpi_norm.tif"), srcDS=vrt_path
        )
        if fb_ds is not None:
            fb_ds = None

    feedback.setProgress(int((progress + 0.8) * status_total))

    tpi_norm = os.path.join(path, "tpi_norm.tif")
    blur_3x3 = os.path.join(path, "dem_blur_3x3.vrt")
    merged_out = os.path.join(path, "merged_contour.tif")

    if smoothing == SMOOTHING_LOW:
        _raster_calc(
            lambda A, B, C: A * B + (1 - A) * C,
            output_path=merged_out,
            nodata=DEM_NODATA,
            overwrite=True,
            A=tpi_norm,
            B=blur_3x3,
            C=os.path.join(path, "dem.tif"),
        )
    elif smoothing == SMOOTHING_MEDIUM:
        temp_files.append(os.path.join(path, "dem_blur_7x7.vrt"))
        _make_blur_vrt(
            os.path.join(path, "dem_blur_7x7.vrt"),
            os.path.join(path, "dem.tif"),
            kernel_size=7,
        )
        _raster_calc(
            lambda A, B, C: A * B + (1 - A) * C,
            output_path=merged_out,
            nodata=DEM_NODATA,
            overwrite=True,
            A=tpi_norm,
            B=blur_3x3,
            C=os.path.join(path, "dem_blur_7x7.vrt"),
        )
    else:
        temp_files.append(os.path.join(path, "dem_blur_13x13.vrt"))
        _make_blur_vrt(
            os.path.join(path, "dem_blur_13x13.vrt"),
            os.path.join(path, "dem.tif"),
            kernel_size=13,
        )
        _raster_calc(
            lambda A, B, C: A * B + (1 - A) * C,
            output_path=merged_out,
            nodata=DEM_NODATA,
            overwrite=True,
            A=tpi_norm,
            B=blur_3x3,
            C=os.path.join(path, "dem_blur_13x13.vrt"),
        )

    feedback.setProgress(int((progress + 1.0) * status_total))

    if tmp_manager is not None:
        for f in temp_files:
            tmp_manager.add_file(f)
    else:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except OSError:
                pass
