# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for contour_smoothing.py — _raster_calc and _make_blur_vrt."""

import os

import numpy as np
import pytest

try:
    from osgeo import gdal
    from unittest.mock import MagicMock
    _REAL_GDAL = not isinstance(gdal, MagicMock)
except ImportError:
    _REAL_GDAL = False

gdalskip = pytest.mark.skipif(
    not _REAL_GDAL, reason="Real GDAL not available (mocked by conftest)",
)

from NoWires.contour.smoothing import _gaussian_kernel_2d, _raster_calc, _make_blur_vrt, smooth_contour_dem


def _create_raster(path, nx=5, ny=5, data_val=100.0):
    if not _REAL_GDAL:
        pytest.skip("Real GDAL not available")
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, nx, ny, 1, gdal.GDT_Float32)
    from osgeo import osr
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform([0.0, 0.1, 0, 1.0, 0, -0.1])
    data = np.full((ny, nx), data_val, dtype=np.float32)
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None
    return path


@pytest.mark.gdal_integration
class TestGaussianKernel2D:
    def test_even_kernel_size(self):
        coefs = _gaussian_kernel_2d(4)
        assert len(coefs.split()) == 16

    def test_custom_sigma(self):
        coefs = _gaussian_kernel_2d(3, sigma=1.0)
        vals = [float(c) for c in coefs.split()]
        assert abs(sum(vals) - 1.0) < 1e-4

    def test_default_sigma(self):
        coefs_9 = _gaussian_kernel_2d(9)
        coefs_9_custom = _gaussian_kernel_2d(9, sigma=0.5)
        assert coefs_9 != coefs_9_custom


@gdalskip
@pytest.mark.gdal_integration
class TestRasterCalc:
    def test_raster_calc_adds_two_rasters(self, tmp_path):
        r1 = str(tmp_path / "r1.tif")
        r2 = str(tmp_path / "r2.tif")
        out = str(tmp_path / "out.tif")
        _create_raster(r1, data_val=10.0)
        _create_raster(r2, data_val=20.0)

        def _add(r1, r2):
            return r1 + r2

        _raster_calc(_add, out, nodata=-32768, r1=r1, r2=r2)
        assert os.path.exists(out)

        ds = gdal.Open(out)
        data = ds.GetRasterBand(1).ReadAsArray()
        assert data[0, 0] == pytest.approx(30.0)
        ds = None

    def test_raster_calc_single_input(self, tmp_path):
        r1 = str(tmp_path / "r1.tif")
        out = str(tmp_path / "out.tif")
        _create_raster(r1, data_val=50.0)

        def _identity(r1):
            return r1 * 2

        _raster_calc(_identity, out, nodata=-32768, r1=r1)
        assert os.path.exists(out)
        ds = gdal.Open(out)
        data = ds.GetRasterBand(1).ReadAsArray()
        assert data[0, 0] == pytest.approx(100.0)
        ds = None

    def test_raster_calc_overwrite_false_raises(self, tmp_path):
        r1 = str(tmp_path / "r1.tif")
        out = str(tmp_path / "out.tif")
        _create_raster(r1)

        def _identity(r1):
            return r1

        _raster_calc(_identity, out, nodata=-32768, overwrite=False, r1=r1)
        with pytest.raises(RuntimeError, match="already exists"):
            _raster_calc(_identity, out, nodata=-32768, overwrite=False, r1=r1)

    def test_raster_calc_overwrite_true(self, tmp_path):
        r1 = str(tmp_path / "r1.tif")
        out = str(tmp_path / "out.tif")
        _create_raster(r1, data_val=30.0)

        def _identity(r1):
            return r1

        _raster_calc(_identity, out, nodata=-32768, overwrite=True, r1=r1)
        _raster_calc(_identity, out, nodata=-32768, overwrite=True, r1=r1)
        assert os.path.exists(out)


@gdalskip
@pytest.mark.gdal_integration
class TestMakeBlurVRT:
    def test_make_blur_vrt_creates_file(self, tmp_path):
        src = str(tmp_path / "src.tif")
        vrt = str(tmp_path / "blur.vrt")
        _create_raster(src, nx=10, ny=10)

        _make_blur_vrt(vrt, src, kernel_size=5)
        assert os.path.exists(vrt)

    def test_make_blur_vrt_valid_xml(self, tmp_path):
        import xml.etree.ElementTree as ET
        src = str(tmp_path / "src.tif")
        vrt = str(tmp_path / "blur.vrt")
        _create_raster(src, nx=10, ny=10)

        _make_blur_vrt(vrt, src, kernel_size=3)
        tree = ET.parse(vrt)
        root = tree.getroot()
        assert root is not None


@gdalskip
@pytest.mark.gdal_integration
class TestSmoothContourDEM:
    def test_smooth_contour_dem_off_skips_processing(self, tmp_path):
        src = str(tmp_path / "src.tif")
        _create_raster(src, nx=8, ny=8, data_val=100.0)

        class _FB:
            def pushInfo(self, m):
                pass
            def setProgress(self, v):
                pass

        result = smooth_contour_dem(
            smoothing="None", input_dem=src,
            temp_dir=str(tmp_path), feedback=_FB(),
            progress=0, status_total=1,
        )
        assert result is None

    def test_smooth_contour_dem_low_produces_merged_file(self, tmp_path):
        src = str(tmp_path / "src.tif")
        _create_raster(src, nx=8, ny=8, data_val=100.0)

        class _FB:
            def pushInfo(self, m):
                pass
            def setProgress(self, v):
                pass

        smooth_contour_dem(
            smoothing="Low", input_dem=src,
            temp_dir=str(tmp_path), feedback=_FB(),
            progress=0, status_total=1,
        )
        merged = os.path.join(str(tmp_path), "merged_contour.tif")
        assert os.path.exists(merged)
