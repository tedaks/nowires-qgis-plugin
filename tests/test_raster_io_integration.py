# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for raster_io.py with real GDAL runtime."""

import os
import sys
import tempfile

import numpy as np
import pytest

try:
    from osgeo import gdal
    from unittest.mock import MagicMock
    _HAS_REAL_GDAL = not isinstance(sys.modules.get("osgeo.gdal", gdal), MagicMock)
except (ImportError, AttributeError):
    _HAS_REAL_GDAL = False
    gdal = None

pytestmark = pytest.mark.skipif(not _HAS_REAL_GDAL, reason="Requires GDAL")


@pytest.mark.gdal_integration
class TestWriteGeotiffIntegration:
    def test_write_geotiff_produces_valid_raster(self):
        from NoWires.raster_io import write_geotiff
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.tif")
            grid = np.random.rand(10, 10).astype(np.float64)
            write_geotiff(path, grid, 14.0, 15.0, 120.0, 121.0)
            ds = gdal.Open(path)
            assert ds is not None
            assert ds.RasterXSize == 10
            assert ds.RasterYSize == 10
            assert ds.GetRasterBand(1).GetNoDataValue() == pytest.approx(-9999.0)
            srs = ds.GetSpatialRef()
            assert srs is not None
            assert "4326" in srs.ExportToWkt()
            del ds

    def test_write_geotiff_sets_geotransform(self):
        from NoWires.raster_io import write_geotiff
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_gt.tif")
            grid = np.ones((5, 8), dtype=np.float64)
            write_geotiff(path, grid, 10.0, 11.0, 100.0, 108.0)
            ds = gdal.Open(path)
            gt = ds.GetGeoTransform()
            assert gt[0] == pytest.approx(100.0)
            assert gt[3] == pytest.approx(11.0)
            assert gt[1] == pytest.approx((108.0 - 100.0) / 8)
            assert gt[5] == pytest.approx(-(11.0 - 10.0) / 5)
            del ds

    def test_write_geotiff_handles_nodata(self):
        from NoWires.raster_io import write_geotiff
        from NoWires.raster_io import grid_to_raster_array
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_nodata.tif")
            grid = np.full((4, 4), float("nan"), dtype=np.float64)
            raster_grid = grid_to_raster_array(grid)
            write_geotiff(path, raster_grid, 20.0, 21.0, 100.0, 101.0)
            ds = gdal.Open(path)
            band = ds.GetRasterBand(1)
            ndv = band.GetNoDataValue()
            assert ndv == pytest.approx(-9999.0)
            data = band.ReadAsArray()
            assert all(v == pytest.approx(-9999.0) for v in data.flat)
            del ds

    def test_write_geotiff_creates_epsg_4326_projection(self):
        from NoWires.raster_io import write_geotiff
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_srs.tif")
            grid = np.ones((3, 3), dtype=np.float64) * 50.0
            write_geotiff(path, grid, 0.0, 1.0, 0.0, 1.0)
            ds = gdal.Open(path)
            srs = ds.GetSpatialRef()
            assert srs is not None
            assert srs.ExportToWkt().find("4326") >= 0
            del ds