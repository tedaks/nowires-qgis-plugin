# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for clutter/grid.py and clutter/advanced.py.

Grid tests (gdal_integration) cover from_raster construction, sampling,
nodata handling, and resolution/bounds from synthetic GeoTIFF fixtures.

Advanced tests cover compute_terminal_clutter_losses with minimal context
and CCH override validation.
"""

import numpy as np
import pytest

from NoWires.clutter.advanced import compute_terminal_clutter_losses
from NoWires.clutter.categories import LEGACY_CLUTTER_CATEGORIES
from NoWires.clutter.context import ClutterLossContext, TerminalClutterLosses
from NoWires.clutter.grid import LandCoverGrid


def _has_real_gdal():
    try:
        from osgeo import gdal
        from unittest.mock import MagicMock
        return not isinstance(gdal, MagicMock)
    except ImportError:
        return False


@pytest.mark.gdal_integration
class TestGridConstructionFromRaster:
    """Construction of LandCoverGrid from a synthetic GeoTIFF raster."""

    def test_grid_construction_from_raster(self, tmp_path):
        if not _has_real_gdal():
            pytest.skip("Real GDAL not available (mocked by conftest)")
        from osgeo import gdal, osr

        tif_path = str(tmp_path / "landcover.tif")
        nx, ny = 8, 6
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tif_path, nx, ny, 1, gdal.GDT_Byte)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetProjection(srs.ExportToWkt())

        west, east = -5.0, 5.0
        north, south = 4.0, -4.0
        dx = (east - west) / nx
        dy = (north - south) / ny
        ds.SetGeoTransform([west, dx, 0, north, 0, -dy])

        raster_data = np.array([
            [10, 20, 30, 40, 50, 60, 70, 80],
            [10, 20, 30, 40, 50, 60, 70, 80],
            [10, 20, 30, 40, 50, 60, 70, 80],
            [10, 20, 30, 40, 50, 60, 70, 80],
            [10, 20, 30, 40, 50, 60, 70, 80],
            [10, 20, 30, 40, 50, 60, 70, 80],
        ], dtype=np.uint8)
        band = ds.GetRasterBand(1)
        band.WriteArray(raster_data)
        band.SetNoDataValue(0)
        band.FlushCache()
        ds = None

        grid = LandCoverGrid.from_raster(tif_path)

        assert grid.data.shape == (ny, nx)
        assert grid.min_lat == pytest.approx(south, abs=0.01)
        assert grid.max_lat == pytest.approx(north, abs=0.01)
        assert grid.min_lon == pytest.approx(west, abs=0.01)
        assert grid.max_lon == pytest.approx(east, abs=0.01)
        assert grid.nodata == 0
        assert grid.source == tif_path


@pytest.mark.gdal_integration
class TestGridSampleReturnsCategory:
    """Sampling a valid land cover pixel returns the expected category."""

    def test_grid_sample_returns_category(self, tmp_path):
        if not _has_real_gdal():
            pytest.skip("Real GDAL not available (mocked by conftest)")
        from osgeo import gdal, osr

        tif_path = str(tmp_path / "lc_sample.tif")
        nx, ny = 4, 3
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tif_path, nx, ny, 1, gdal.GDT_Byte)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetProjection(srs.ExportToWkt())

        west, east = -4.0, 4.0
        north, south = 3.0, -3.0
        dx = (east - west) / nx
        dy = (north - south) / ny
        ds.SetGeoTransform([west, dx, 0, north, 0, -dy])

        raster_data = np.array([
            [10, 20, 30, 50],
            [40, 50, 60, 70],
            [80, 10, 20, 40],
        ], dtype=np.uint8)
        band = ds.GetRasterBand(1)
        band.WriteArray(raster_data)
        band.SetNoDataValue(0)
        band.FlushCache()
        ds = None

        grid = LandCoverGrid.from_raster(tif_path)

        sampled = grid.sample_category(0.0, 0.0)
        assert sampled is not None
        assert isinstance(sampled, str)
        assert sampled in LEGACY_CLUTTER_CATEGORIES

    def test_grid_sample_returns_none_for_nodata(self, tmp_path):
        if not _has_real_gdal():
            pytest.skip("Real GDAL not available (mocked by conftest)")
        from osgeo import gdal, osr

        tif_path = str(tmp_path / "lc_nodata.tif")
        nx, ny = 3, 3
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tif_path, nx, ny, 1, gdal.GDT_Byte)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetProjection(srs.ExportToWkt())

        west, east = -3.0, 3.0
        north, south = 3.0, -3.0
        dx = (east - west) / nx
        dy = (north - south) / ny
        ds.SetGeoTransform([west, dx, 0, north, 0, -dy])

        raster_data = np.array([
            [10, 20, 30],
            [40, 0, 60],
            [70, 80, 10],
        ], dtype=np.uint8)
        band = ds.GetRasterBand(1)
        band.WriteArray(raster_data)
        band.SetNoDataValue(0)
        band.FlushCache()
        ds = None

        grid = LandCoverGrid.from_raster(tif_path)

        assert grid.sample_category(0.0, 0.0) is None


@pytest.mark.gdal_integration
class TestGridResolutionAndBounds:
    """Verify grid width, height, and lat/lon bounds from synthetic tile."""

    def test_grid_resolution_and_bounds(self, tmp_path):
        if not _has_real_gdal():
            pytest.skip("Real GDAL not available (mocked by conftest)")
        from osgeo import gdal, osr

        tif_path = str(tmp_path / "lc_bounds.tif")
        nx, ny = 12, 7
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tif_path, nx, ny, 1, gdal.GDT_Byte)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetProjection(srs.ExportToWkt())

        west, east = -10.0, 10.0
        north, south = 7.0, -7.0
        dx = (east - west) / nx
        dy = (north - south) / ny
        ds.SetGeoTransform([west, dx, 0, north, 0, -dy])

        raster_data = np.full((ny, nx), 20, dtype=np.uint8)
        band = ds.GetRasterBand(1)
        band.WriteArray(raster_data)
        band.SetNoDataValue(255)
        band.FlushCache()
        ds = None

        grid = LandCoverGrid.from_raster(tif_path)

        assert grid.data.shape == (ny, nx)
        assert grid.data.shape[0] == 7
        assert grid.data.shape[1] == 12
        assert grid.min_lat == pytest.approx(-7.0, abs=0.1)
        assert grid.max_lat == pytest.approx(7.0, abs=0.1)
        assert grid.min_lon == pytest.approx(-10.0, abs=0.1)
        assert grid.max_lon == pytest.approx(10.0, abs=0.1)


class TestAdvancedClutterBuildsFromContext:
    """Advanced clutter losses from compute_terminal_clutter_losses with
    minimal ClutterLossContext and manual category overrides.
    """

    def test_advanced_clutter_builds_from_context(self):
        ctx = ClutterLossContext(
            frequency_mhz=900.0,
            distance_m=3000.0,
            tx_height_m=30.0,
            rx_height_m=2.0,
            model="advanced",
            percentile=50.0,
            rx_ground_elevation_m=0.0,
            polarization=0,
        )
        result = compute_terminal_clutter_losses(
            tx_lat=14.0, tx_lon=121.0,
            rx_lat=14.1, rx_lon=121.1,
            frequency_mhz=900.0,
            enabled=True,
            tx_override="suburban",
            rx_override="urban",
            context=ctx,
        )
        assert isinstance(result, TerminalClutterLosses)
        assert result.tx_category != "open"
        assert result.rx_category != "open"
        assert result.total_loss_db >= 0.0

    def test_advanced_clutter_with_cch_override(self):
        ctx_no_override = ClutterLossContext(
            frequency_mhz=900.0,
            distance_m=3000.0,
            tx_height_m=30.0,
            rx_height_m=2.0,
            model="advanced",
            percentile=50.0,
            rx_ground_elevation_m=0.0,
            polarization=0,
        )
        result_no_override = compute_terminal_clutter_losses(
            tx_lat=14.0, tx_lon=121.0,
            rx_lat=14.1, rx_lon=121.1,
            frequency_mhz=900.0,
            enabled=True,
            tx_override="suburban",
            rx_override="urban",
            context=ctx_no_override,
        )

        ctx_with_cch = ClutterLossContext(
            frequency_mhz=900.0,
            distance_m=3000.0,
            tx_height_m=30.0,
            rx_height_m=2.0,
            model="advanced",
            percentile=50.0,
            rx_ground_elevation_m=0.0,
            polarization=0,
            cch_override_m=5.0,
        )
        result_with_cch = compute_terminal_clutter_losses(
            tx_lat=14.0, tx_lon=121.0,
            rx_lat=14.1, rx_lon=121.1,
            frequency_mhz=900.0,
            enabled=True,
            tx_override="suburban",
            rx_override="urban",
            context=ctx_with_cch,
        )

        assert isinstance(result_no_override, TerminalClutterLosses)
        assert isinstance(result_with_cch, TerminalClutterLosses)
        assert result_with_cch.rx_cch_m == 5.0
        assert result_with_cch.tx_cch_m == 5.0
        assert result_no_override.rx_cch_m != 5.0
        assert result_no_override.tx_cch_m != 5.0
