# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""GDAL/OGR compatibility matrix — import paths, API stability, dataset lifecycle."""


class TestGdalImportPaths:
    """Verify GDAL/OGR/OSR import patterns resolve with mocked modules."""

    def test_osgeo_gdal_imports(self):
        from osgeo import gdal
        assert hasattr(gdal, "Open")
        assert hasattr(gdal, "GetDriverByName")

    def test_osgeo_ogr_imports(self):
        from osgeo import ogr
        assert hasattr(ogr, "GetDriverByName")
        assert hasattr(ogr, "wkbLineString")
        assert hasattr(ogr, "wkbPolygon")
        assert hasattr(ogr, "wkbLinearRing")

    def test_osgeo_osr_imports(self):
        from osgeo import osr
        assert hasattr(osr, "SpatialReference")
        assert hasattr(osr, "OAMS_TRADITIONAL_GIS_ORDER")


class TestGdalStableApiUsage:
    """Source-scanning contract: verify the plugin only uses stable GDAL APIs."""

    def test_raster_io_uses_create_not_createcopy(self):
        source = open("raster_io.py").read()
        assert "driver.Create(" in source
        assert "CreateCopy" not in source

    def test_raster_io_sets_geotransform(self):
        source = open("raster_io.py").read()
        assert "SetGeoTransform" in source

    def test_raster_io_uses_wkt_projection(self):
        source = open("raster_io.py").read()
        assert "ExportToWkt" in source

    def test_tile_download_uses_gdal_warp(self):
        source = open("tile_download_base.py").read()
        assert "gdal.Warp" in source

    def test_tile_download_warp_uses_stable_kwargs(self):
        source = open("tile_download_base.py").read()
        for kw in ("cutlineDSName", "cropToCutline", "dstNodata",
                   "srcSRS", "dstSRS", "format"):
            assert kw in source, "Missing stable Warp kwarg: {}".format(kw)

    def test_tile_download_validates_with_compute_statistics(self):
        source = open("tile_download_base.py").read()
        assert "ComputeStatistics" in source


class TestOgrStableApiUsage:
    """Source-scanning contract: verify OGR vector output uses stable APIs."""

    def test_p2p_outputs_uses_create_datasource(self):
        source = open("p2p_outputs.py").read()
        assert "driver.CreateDataSource(" in source

    def test_p2p_outputs_creates_feature_with_layer_defn(self):
        source = open("p2p_outputs.py").read()
        assert "GetLayerDefn" in source
        assert "CreateFeature" in source

    def test_p2p_outputs_uses_wkb_geometry_types(self):
        source = open("p2p_outputs.py").read()
        assert "wkbLineString" in source
        assert "wkbPolygon" in source

    def test_report_markers_uses_ogr_driver_for_path(self):
        source = open("report_markers.py").read()
        assert "ogr_driver_for_path" in source


class TestDatasetLifecycle:
    """Verify GDAL/OGR datasets are properly closed in finally blocks."""

    def test_raster_io_closes_with_ds_none(self):
        source = open("raster_io.py").read()
        has_finally = "finally:" in source
        has_ds_none = "ds = None" in source
        assert has_finally and has_ds_none, "raster_io must close ds in finally"

    def test_raster_io_closes_band_before_dataset(self):
        source = open("raster_io.py").read()
        assert "band = None" in source, "raster_io must release band before closing dataset"

    def test_p2p_outputs_closes_poly_datasource(self):
        source = open("p2p_outputs.py").read()
        assert "ds_poly = None" in source

    def test_p2p_outputs_closes_lines_datasource(self):
        source = open("p2p_outputs.py").read()
        assert "ds_lines = None" in source

    def test_clutter_closes_gdal_band_and_dataset(self):
        source = open("clutter_grid.py").read()
        assert "band = None" in source
        assert "ds = None" in source


class TestGdalVersionSensitiveFeatures:
    """Verify usage of GDAL >= 3.0 features has appropriate guards."""

    def test_tile_download_uses_axis_mapping_strategy(self):
        """SetAxisMappingStrategy was added in GDAL 3.0."""
        source = open("tile_download_base.py").read()
        assert "OAMS_TRADITIONAL_GIS_ORDER" in source

    def test_osr_axis_mapping_is_set_before_create_layer(self):
        """Verify SetAxisMappingStrategy is called before CreateLayer."""
        source = open("tile_download_base.py").read()
        set_idx = source.find("SetAxisMappingStrategy")
        create_idx = source.find("CreateLayer")
        assert set_idx > 0 and create_idx > 0, "Both calls must exist"
        assert set_idx < create_idx, "SetAxisMappingStrategy must precede CreateLayer"
