# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for contour_overlay module.

GDAL-dependent tests verify the overlay raster pipeline.
These require a real QGIS/GDAL runtime.
"""

import os

import numpy as np
import pytest

from contour_overlay import prepare_elevation_overlay

pytestmark = [pytest.mark.qgis_integration]


class TestContourOverlayContract:
    def test_module_imports_successfully(self):
        assert callable(prepare_elevation_overlay)


@pytest.mark.gdal_integration
class TestContourOverlayGDAL:
    def _create_dem(self, path, width=20, height=20):
        from osgeo import gdal, osr
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, width, height, 1, gdal.GDT_Float32)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform([8.0, 0.001, 0, 47.01, 0, -0.001])
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(-32768)
        data = np.full((height, width), 500.0, dtype=np.float32)
        band.WriteArray(data)
        band.FlushCache()
        ds = None
        return path

    def test_prepare_overlay_produces_hillshade(self, tmp_path):
        from osgeo import gdal
        from unittest.mock import MagicMock
        dem_path = self._create_dem(str(tmp_path / "dem.tif"))
        context = MagicMock()
        context.project.return_value.crs.return_value.authid.return_value = "EPSG:4326"
        context.project.return_value.crs.return_value.isValid.return_value = True
        feedback = MagicMock()

        result_path = prepare_elevation_overlay(
            dem_path, str(tmp_path), context, feedback)
        assert os.path.exists(result_path)
        result_ds = gdal.Open(result_path)
        assert result_ds is not None
        assert result_ds.RasterXSize > 0
        assert result_ds.RasterYSize > 0
        result_ds = None

    def test_prepare_overlay_has_overviews(self, tmp_path):
        from osgeo import gdal
        from unittest.mock import MagicMock
        dem_path = self._create_dem(str(tmp_path / "dem.tif"))
        context = MagicMock()
        context.project.return_value.crs.return_value.authid.return_value = "EPSG:4326"
        context.project.return_value.crs.return_value.isValid.return_value = True
        feedback = MagicMock()

        result_path = prepare_elevation_overlay(
            dem_path, str(tmp_path), context, feedback)
        result_ds = gdal.Open(result_path)
        band = result_ds.GetRasterBand(1)
        overview_count = band.GetOverviewCount()
        assert overview_count >= 0
        result_ds = None