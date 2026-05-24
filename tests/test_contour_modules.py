# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for contour/generation.py and contour/smoothing.py."""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.qgis_integration


def _make_sloped_dem(path, nx=50, ny=50):
    from osgeo import gdal, osr
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, nx, ny, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform([0.0, 0.01, 0, 1.0, 0, -0.01])
    data = np.zeros((ny, nx), dtype=np.float32)
    for y in range(ny):
        data[y, :] = float(y) * 2.0
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None


class Feedback:
    def __init__(self):
        self.messages = []

    def pushInfo(self, msg):
        self.messages.append(msg)

    def pushWarning(self, msg):
        self.messages.append(msg)

    def isCanceled(self):
        return False

    def setProgress(self, val):
        pass


class TestContourGeneration:
    def test_generate_contour_lines(self, qgis_app, tmp_path):
        from NoWires.contour.generation import generate_contour_lines
        from NoWires.temp_manager import TempDirManager

        dem = str(tmp_path / "dem.tif")
        _make_sloped_dem(dem)
        mgr = TempDirManager()
        tmp_dir = mgr.make_dir("contour_gen")

        try:
            out_path = generate_contour_lines(
                merged_path=dem,
                interval=50.0,
                temp_dir=tmp_dir,
                gdal_callback=None,
            )
            assert out_path is not None
        finally:
            mgr.cleanup()


class TestContourSmoothing:
    def test_smooth_contour_dem_low(self, qgis_app, tmp_path):
        from NoWires.contour.smoothing import smooth_contour_dem, SMOOTHING_LOW
        from NoWires.temp_manager import TempDirManager

        dem = str(tmp_path / "smooth_in.tif")
        _make_sloped_dem(dem)
        mgr = TempDirManager()
        tmp_dir = mgr.make_dir("smooth_low")

        try:
            smooth_contour_dem(
                SMOOTHING_LOW, dem, tmp_dir,
                Feedback(), 0.0, 1.0,
                tmp_manager=mgr,
            )
            merged = os.path.join(tmp_dir, "merged_contour.tif")
            assert os.path.exists(merged)
        finally:
            mgr.cleanup()

    def test_smooth_contour_dem_medium(self, qgis_app, tmp_path):
        from NoWires.contour.smoothing import smooth_contour_dem, SMOOTHING_MEDIUM
        from NoWires.temp_manager import TempDirManager

        dem = str(tmp_path / "smooth_med.tif")
        _make_sloped_dem(dem)
        mgr = TempDirManager()
        tmp_dir = mgr.make_dir("smooth_med")

        try:
            smooth_contour_dem(
                SMOOTHING_MEDIUM, dem, tmp_dir,
                Feedback(), 0.0, 1.0,
                tmp_manager=mgr,
            )
            merged = os.path.join(tmp_dir, "merged_contour.tif")
            assert os.path.exists(merged)
        finally:
            mgr.cleanup()

    def test_smooth_contour_dem_high(self, qgis_app, tmp_path):
        from NoWires.contour.smoothing import smooth_contour_dem, SMOOTHING_HIGH
        from NoWires.temp_manager import TempDirManager

        dem = str(tmp_path / "smooth_high.tif")
        _make_sloped_dem(dem)
        mgr = TempDirManager()
        tmp_dir = mgr.make_dir("smooth_high")

        try:
            smooth_contour_dem(
                SMOOTHING_HIGH, dem, tmp_dir,
                Feedback(), 0.0, 1.0,
                tmp_manager=mgr,
            )
            merged = os.path.join(tmp_dir, "merged_contour.tif")
            assert os.path.exists(merged)
        finally:
            mgr.cleanup()
