# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for contour_generation module.

GDAL-dependent tests create a minimal DEM raster and verify contour generation.
These require a real QGIS/GDAL runtime and are skipped in the unit test runner.
"""

import os

import numpy as np
import pytest

pytestmark = [pytest.mark.qgis_integration]


class TestContourGenerationContract:
    def test_module_imports_generate(self):
        from contour_generation import generate_contour_lines
        assert callable(generate_contour_lines)

    def test_module_imports_reproject(self):
        from contour_generation import reproject_and_export
        assert callable(reproject_and_export)


class TestContourGenerationGDAL:
    def _create_dem(self, path, width=20, height=20, pixel_size=0.001, origin_x=8.0, origin_y=47.0):
        from osgeo import gdal, osr
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, width, height, 1, gdal.GDT_Float32)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform([origin_x, pixel_size, 0, origin_y, 0, -pixel_size])
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(-32768)
        data = np.full((height, width), 100.0, dtype=np.float32)
        for row in range(height):
            data[row, :] = 100.0 + row * 10.0
        band.WriteArray(data)
        band.FlushCache()
        ds = None
        return path

    def test_generate_contour_lines_produces_shapefile(self, tmp_path):
        from osgeo import ogr
        from contour_generation import generate_contour_lines
        dem_path = self._create_dem(str(tmp_path / "test_dem.tif"))
        out_dir = str(tmp_path / "contours_out")
        os.makedirs(out_dir, exist_ok=True)
        shp_path, _ = generate_contour_lines(dem_path, 50, out_dir, None)
        assert os.path.exists(shp_path)
        shp_ds = ogr.Open(shp_path)
        assert shp_ds is not None
        layer = shp_ds.GetLayer(0)
        assert layer.GetFeatureCount() > 0
        assert layer.GetLayerDefn().GetFieldIndex("ELEV") >= 0
        assert layer.GetLayerDefn().GetFieldIndex("ID") >= 0
        shp_ds = None

    def test_contour_lines_have_valid_geometry(self, tmp_path):
        from osgeo import ogr
        from contour_generation import generate_contour_lines
        dem_path = self._create_dem(str(tmp_path / "test_dem.tif"))
        out_dir = str(tmp_path / "contours_out2")
        os.makedirs(out_dir, exist_ok=True)
        shp_path, _ = generate_contour_lines(dem_path, 50, out_dir, None)
        shp_ds = ogr.Open(shp_path)
        layer = shp_ds.GetLayer(0)
        for feat in layer:
            geom = feat.GetGeometryRef()
            assert geom is not None
            assert geom.GetGeometryType() in (ogr.wkbLineString, ogr.wkbLineString25D)
        shp_ds = None

    def test_contour_lines_have_srs_4326(self, tmp_path):
        from osgeo import ogr
        from contour_generation import generate_contour_lines
        dem_path = self._create_dem(str(tmp_path / "test_dem.tif"))
        out_dir = str(tmp_path / "contours_out3")
        os.makedirs(out_dir, exist_ok=True)
        shp_path, _ = generate_contour_lines(dem_path, 50, out_dir, None)
        shp_ds = ogr.Open(shp_path)
        layer = shp_ds.GetLayer(0)
        srs = layer.GetSpatialRef()
        assert srs is not None
        auth = srs.GetAuthorityCode(None)
        assert auth == "4326"
        shp_ds = None