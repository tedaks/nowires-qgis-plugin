# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for non-Qt paths in three_d, report/markers, and p2p/chart_format."""

import os



class TestThreeDHelpers:
    def test_next_3d_view_name_first(self):
        from three_d import _next_3d_view_name
        name = _next_3d_view_name(None)
        assert name == "NoWires 3D View 1"

    def test_next_3d_view_name_unique(self):
        from three_d import _next_3d_view_name
        names = set()
        for _ in range(5):
            names.add(_next_3d_view_name(None))
        assert len(names) == 1


class TestShapefileSidecars:
    def test_remove_shapefile_sidecars_removes_prj(self, tmp_path):
        from report.markers import _remove_shapefile_sidecars
        base = str(tmp_path / "test")
        shp_path = base + ".shp"
        with open(shp_path, "w") as f:
            f.write("dummy")
        for ext in (".shx", ".dbf", ".prj", ".cpg"):
            with open(base + ext, "w") as f:
                f.write("")
        _remove_shapefile_sidecars(shp_path)
        assert os.path.exists(shp_path)
        assert not os.path.exists(base + ".shx")
        assert not os.path.exists(base + ".dbf")
        assert not os.path.exists(base + ".prj")
        assert not os.path.exists(base + ".cpg")

    def test_remove_shapefile_sidecars_no_crash_on_missing(self, tmp_path):
        from report.markers import _remove_shapefile_sidecars
        base = str(tmp_path / "nonexistent.shp")
        _remove_shapefile_sidecars(base)
        assert True

    def test_remove_shapefile_sidecars_with_cpg(self, tmp_path):
        from report.markers import _remove_shapefile_sidecars
        base = str(tmp_path / "cpg_test")
        shp_path = base + ".shp"
        with open(shp_path, "w") as f:
            f.write("dummy")
        with open(base + ".cpg", "w") as f:
            f.write("")
        _remove_shapefile_sidecars(shp_path)
        assert os.path.exists(shp_path)
        assert not os.path.exists(base + ".cpg")


class TestOGRDriverForPath:
    def test_shapefile_returns_esri_shapefile(self):
        from report.markers import ogr_driver_for_path
        assert ogr_driver_for_path("test.shp") == "ESRI Shapefile"

    def test_geopackage_returns_gpkg(self):
        from report.markers import ogr_driver_for_path
        assert ogr_driver_for_path("test.gpkg") == "GPKG"

    def test_geojson_returns_geojson(self):
        from report.markers import ogr_driver_for_path
        assert ogr_driver_for_path("test.geojson") == "GeoJSON"

    def test_unknown_extension_defaults_to_gpkg(self):
        from report.markers import ogr_driver_for_path
        assert ogr_driver_for_path("test.xyz") == "GPKG"


class TestRemoveExistingOGRDataset:
    def test_non_existing_path_no_error(self, tmp_path):
        from osgeo import ogr
        from report.markers import remove_existing_ogr_dataset
        driver = ogr.GetDriverByName("GPKG")
        remove_existing_ogr_dataset(driver, str(tmp_path / "nonexistent.gpkg"))

    def test_none_driver_no_error(self):
        from report.markers import remove_existing_ogr_dataset
        remove_existing_ogr_dataset(None, "/does/not/exist.gpkg")


class TestBuildP2PMarkerRecords:
    def test_build_marker_records_tx_rx(self):
        from report.markers import build_p2p_marker_records
        records = build_p2p_marker_records(
            tx_lat=47.0, tx_lon=8.0, rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0,
            tx_gain=5.0, rx_gain=3.0,
            tx_power_dbm=30.0, rx_sensitivity_dbm=-50.0,
        )
        assert len(records) == 2
        assert records[0]["role"] == "TX"
        assert records[1]["role"] == "RX"
