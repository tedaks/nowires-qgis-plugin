# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for clutter_grid.py — LandCoverGrid sampling, lifecycle, and vectorised lookups."""

import numpy as np
import pytest

from NoWires.clutter.grid import LandCoverGrid
from NoWires.clutter.categories import LEGACY_CLUTTER_CATEGORIES, LEGACY_CLUTTER_LOSS_DB
from NoWires.clutter.categories import ADVANCED_CLUTTER_CATEGORIES


_OPEN_RURAL = "open_rural"
_VEGETATION = "vegetation"
_URBAN = "urban"


def _make_grid(data=None, nodata=None):
    if data is None:
        data = np.array([
            [10, 20, 30, 40, 50],
            [10, 20, 30, 40, 50],
            [10, 20, 30, 40, 50],
        ], dtype=np.uint8)
    grid = LandCoverGrid(
        data=data,
        min_lat=-9.0, max_lat=9.0,
        min_lon=-9.0, max_lon=9.0,
        nodata=nodata,
        source="test",
    )
    return grid


class TestLandCoverGridInit:
    def test_constructor_sets_all_attributes(self):
        data = np.array([[10, 20]], dtype=np.uint8)
        g = LandCoverGrid(data, -1.0, 2.0, -3.0, 4.0, nodata=255, source="test_source")
        assert g.data is data
        assert g.min_lat == -1.0
        assert g.max_lat == 2.0
        assert g.min_lon == -3.0
        assert g.max_lon == 4.0
        assert g.nodata == 255
        assert g.source == "test_source"


class TestLandCoverGridSampleClass:
    def test_sample_class_returns_correct_worldcover_id(self):
        g = _make_grid()
        val = g.sample_class(0.0, 0.0)
        assert val == 30

    def test_sample_class_oob_returns_none(self):
        g = _make_grid()
        assert g.sample_class(90.0, 0.0) is None
        assert g.sample_class(-90.0, 0.0) is None
        assert g.sample_class(0.0, 90.0) is None
        assert g.sample_class(0.0, -90.0) is None

    def test_sample_class_nodata_returns_none(self):
        data = np.array([[10, 10, 10], [10, 255, 10], [10, 10, 10]], dtype=np.uint8)
        g = _make_grid(data=data, nodata=255)
        assert g.sample_class(0.0, 0.0) is None

    def test_sample_class_closed_raises(self):
        g = _make_grid()
        g.close()
        with pytest.raises(RuntimeError, match="closed"):
            g.sample_class(0.0, 0.0)

    def test_sample_class_boundary(self):
        g = _make_grid()
        assert g.sample_class(g.max_lat, g.min_lon) is not None
        assert g.sample_class(g.min_lat, g.max_lon) is not None

    def test_nodata_nan_handling(self):
        data = np.array([[10, 20], [30, 40]], dtype=np.float32)
        g = _make_grid(data=data, nodata=30.0)
        val = g.sample_class(0.0, 0.0)
        assert val is not None


class TestLandCoverGridSampleCategory:
    def test_sample_category_returns_legacy_category(self):
        g = _make_grid()
        cat = g.sample_category(0.0, 0.0)
        assert cat in LEGACY_CLUTTER_CATEGORIES

    def test_sample_category_oob_returns_none(self):
        g = _make_grid()
        assert g.sample_category(90.0, 0.0) is None

    def test_sample_category_worldcover_10_is_vegetation(self):
        data = np.array([[10]], dtype=np.uint8)
        g = _make_grid(data=data)
        assert g.sample_category(0.0, 0.0) == _VEGETATION

    def test_sample_category_worldcover_50_is_urban(self):
        data = np.array([[50]], dtype=np.uint8)
        g = _make_grid(data=data)
        assert g.sample_category(0.0, 0.0) == _URBAN


class TestLandCoverGridSampleCategoryGrid:
    def test_simple_mode_returns_loss_array(self):
        data = np.full((5, 5), 10, dtype=np.uint8)
        g = _make_grid(data=data)
        lats = np.array([-8.0, 0.0, 8.0])
        lons = np.array([-8.0, 0.0, 8.0])
        result = g.sample_category_grid(lats, lons, rx_override=None, context=None)
        assert result.shape == (3, 3)
        assert result.dtype == np.float64
        assert result[1, 1] > 0

    def test_simple_mode_with_override(self):
        data = np.full((5, 5), 10, dtype=np.uint8)
        g = _make_grid(data=data)
        lats = np.array([0.0])
        lons = np.array([0.0])
        result = g.sample_category_grid(lats, lons, rx_override="urban", context=None)
        assert result[0, 0] == LEGACY_CLUTTER_LOSS_DB["urban"]

    def test_advanced_mode_returns_category_array(self):
        from NoWires.clutter.context import ClutterLossContext
        data = np.full((5, 5), 50, dtype=np.uint8)
        g = _make_grid(data=data)
        lats = np.array([0.0])
        lons = np.array([0.0])
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=5000.0,
            tx_height_m=30.0, rx_height_m=10.0,
            model="advanced",
        )
        result = g.sample_category_grid(lats, lons, rx_override=None, context=ctx)
        assert result.shape == (1, 1)
        assert result[0, 0] in ADVANCED_CLUTTER_CATEGORIES

    def test_advanced_mode_with_rx_override(self):
        from NoWires.clutter.context import ClutterLossContext
        data = np.full((5, 5), 10, dtype=np.uint8)
        g = _make_grid(data=data)
        lats = np.array([0.0, 8.0])
        lons = np.array([0.0, 8.0])
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=5000.0,
            tx_height_m=30.0, rx_height_m=10.0,
            model="advanced",
        )
        result = g.sample_category_grid(lats, lons, rx_override="urban", context=ctx)
        assert result[0, 0] == "urban"
        assert result[0, 1] == "urban"

    def test_out_of_bounds_returns_open(self):
        data = np.full((5, 5), 50, dtype=np.uint8)
        g = _make_grid(data=data)
        lats = np.array([90.0])
        lons = np.array([0.0])
        result = g.sample_category_grid(lats, lons, rx_override=None, context=None)
        assert result[0, 0] == 0.0

    def test_closed_grid_raises(self):
        g = _make_grid()
        g.close()
        lats = np.array([0.0])
        lons = np.array([0.0])
        with pytest.raises(RuntimeError, match="closed"):
            g.sample_category_grid(lats, lons)

    def test_advanced_mode_oob_returns_open(self):
        from NoWires.clutter.context import ClutterLossContext
        data = np.full((5, 5), 50, dtype=np.uint8)
        g = _make_grid(data=data)
        lats = np.array([90.0])
        lons = np.array([0.0])
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=5000.0,
            tx_height_m=30.0, rx_height_m=10.0,
            model="advanced",
        )
        result = g.sample_category_grid(lats, lons, context=ctx)
        assert result[0, 0] == "open"


class TestLandCoverGridLifecycle:
    def test_context_manager_works(self):
        g = _make_grid()
        with g:
            assert g.data is not None
        assert g.data is None

    def test_close_nulls_data(self):
        g = _make_grid()
        g.close()
        assert g.data is None
        g.close()
        assert g.data is None

    def test_enter_returns_self(self):
        g = _make_grid()
        assert g.__enter__() is g

    def test_exit_calls_close(self):
        g = _make_grid()
        g.__exit__(None, None, None)
        assert g.data is None


@pytest.mark.gdal_integration
class TestLandCoverGridFromRaster:
    def test_from_raster_creates_grid(self, tmp_path):
        try:
            from osgeo import gdal
            from unittest.mock import MagicMock
            if isinstance(gdal, MagicMock):
                pytest.skip("osgeo.gdal is mocked by conftest")
        except ImportError:
            pytest.skip("GDAL not available")

        tif_path = str(tmp_path / "lc.tif")
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tif_path, 4, 3, 1, gdal.GDT_Byte)
        srs = gdal.osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform([-6.0, 4.0, 0.0, 6.0, 0.0, -4.0])
        data = np.array([
            [10, 20, 30, 40],
            [50, 10, 20, 30],
            [40, 50, 10, 20],
        ], dtype=np.uint8)
        band = ds.GetRasterBand(1)
        band.WriteArray(data)
        band.SetNoDataValue(0)
        band.FlushCache()
        ds = None

        grid = LandCoverGrid.from_raster(tif_path)
        assert grid.data.shape == (3, 4)
        assert grid.min_lat == -6.0
        assert grid.max_lat == 6.0
        assert grid.source == tif_path

    def test_from_raster_south_up_flip(self, tmp_path):
        try:
            from osgeo import gdal
            from unittest.mock import MagicMock
            if isinstance(gdal, MagicMock):
                pytest.skip("osgeo.gdal is mocked by conftest")
        except ImportError:
            pytest.skip("GDAL not available")

        tif_path = str(tmp_path / "lc_south.tif")
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tif_path, 2, 2, 1, gdal.GDT_Byte)
        srs = gdal.osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform([0.0, 1.0, 0.0, 0.0, 0.0, 1.0])
        data = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        band = ds.GetRasterBand(1)
        band.WriteArray(data)
        band.FlushCache()
        ds = None

        grid = LandCoverGrid.from_raster(tif_path)
        assert grid.data[0, 0] != data[0, 0]
