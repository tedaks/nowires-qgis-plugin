# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for report_markers.py — OGR marker output helpers.

Requires a real GDAL/OGR runtime (QGIS Docker container).  The conftest
mocks osgeo when QGIS is unavailable, so these tests only work in the
QGIS integration environment.
"""

try:
    from osgeo import ogr, osr
    from unittest.mock import MagicMock
    _IS_MOCK = isinstance(ogr, MagicMock)
    _REAL_GDAL = not _IS_MOCK
except Exception:
    _REAL_GDAL = False

import pytest

if _REAL_GDAL:
    from NoWires.report.markers import (
        ogr_driver_for_path,
        remove_existing_ogr_dataset,
        build_p2p_marker_records,
        write_p2p_marker_layer,
        write_single_marker,
    )

pytestmark = [
    pytest.mark.skipif(not _REAL_GDAL, reason="Real OGR/GDAL not available (mocked by conftest)"),
    pytest.mark.qgis_integration,
]


def _make_srs():
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


class TestOGRDriverForPath:
    def test_shp_returns_shapefile(self):
        assert ogr_driver_for_path("output.shp") == "ESRI Shapefile"

    def test_gpkg_returns_gpkg(self):
        assert ogr_driver_for_path("output.gpkg") == "GPKG"

    def test_geojson_returns_geojson(self):
        assert ogr_driver_for_path("output.geojson") == "GeoJSON"

    def test_json_returns_geojson(self):
        assert ogr_driver_for_path("output.json") == "GeoJSON"

    def test_kml_returns_kml(self):
        assert ogr_driver_for_path("output.kml") == "KML"

    def test_unknown_extension_returns_gpkg(self):
        assert ogr_driver_for_path("output.xyz") == "GPKG"

    def test_no_extension_returns_gpkg(self):
        assert ogr_driver_for_path("output") == "GPKG"

    def test_case_insensitive(self):
        assert ogr_driver_for_path("output.SHP") == "ESRI Shapefile"
        assert ogr_driver_for_path("output.GeoJSON") == "GeoJSON"


class TestRemoveExistingOGRDataset:
    def test_removes_existing_dataset(self, tmp_path):
        path = str(tmp_path / "test.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(path)
        ds.CreateLayer("test", geom_type=ogr.wkbPoint)
        ds = None
        assert (tmp_path / "test.gpkg").exists()
        remove_existing_ogr_dataset(driver, path)
        assert not (tmp_path / "test.gpkg").exists()

    def test_no_error_on_nonexistent_path(self):
        driver = ogr.GetDriverByName("GPKG")
        remove_existing_ogr_dataset(driver, "/tmp/nonexistent_xyz123.gpkg")


class TestBuildP2PMarkerRecords:
    def test_returns_two_records(self):
        records = build_p2p_marker_records(
            tx_lat=47.0, tx_lon=8.0,
            rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0,
            tx_gain=5.0, rx_gain=2.0,
            tx_power_dbm=36.0,
            rx_sensitivity_dbm=-90.0,
        )
        assert len(records) == 2

    def test_tx_record_has_correct_fields(self):
        records = build_p2p_marker_records(
            tx_lat=47.0, tx_lon=8.0,
            rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0,
            tx_gain=5.0, rx_gain=2.0,
            tx_power_dbm=36.0,
            rx_sensitivity_dbm=-90.0,
        )
        tx = records[0]
        assert tx["role"] == "TX"
        assert tx["latitude"] == 47.0
        assert tx["longitude"] == 8.0
        assert tx["height_m"] == 30.0
        assert tx["gain_dbi"] == 5.0
        assert tx["power_dbm"] == 36.0
        assert tx["sensitivity_dbm"] is None

    def test_rx_record_has_correct_fields(self):
        records = build_p2p_marker_records(
            tx_lat=47.0, tx_lon=8.0,
            rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0,
            tx_gain=5.0, rx_gain=2.0,
            tx_power_dbm=36.0,
            rx_sensitivity_dbm=-90.0,
        )
        rx = records[1]
        assert rx["role"] == "RX"
        assert rx["latitude"] == 47.1
        assert rx["longitude"] == 8.1
        assert rx["height_m"] == 10.0
        assert rx["gain_dbi"] == 2.0
        assert rx["power_dbm"] is None
        assert rx["sensitivity_dbm"] == -90.0


class TestWriteP2PMarkerLayer:
    def test_creates_gpkg_with_two_features(self, tmp_path):
        path = str(tmp_path / "markers.gpkg")
        result_path = write_p2p_marker_layer(
            path=path,
            tx_lat=47.0, tx_lon=8.0,
            rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0,
            tx_gain=5.0, rx_gain=2.0,
            tx_power_dbm=36.0,
            rx_sensitivity_dbm=-90.0,
        )
        assert result_path == path
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        assert layer.GetFeatureCount() == 2
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsString("role") in ("TX", "RX")
        ds = None

    def test_geometry_is_point(self, tmp_path):
        path = str(tmp_path / "markers.gpkg")
        write_p2p_marker_layer(
            path=path,
            tx_lat=47.0, tx_lon=8.0,
            rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0,
            tx_gain=5.0, rx_gain=2.0,
            tx_power_dbm=36.0,
            rx_sensitivity_dbm=-90.0,
        )
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        feat = layer.GetNextFeature()
        geom = feat.GetGeometryRef()
        assert geom.GetGeometryName() == "POINT"
        ds = None

    def test_overwrites_existing_file(self, tmp_path):
        path = str(tmp_path / "markers.gpkg")
        write_p2p_marker_layer(
            path=path, tx_lat=0, tx_lon=0, rx_lat=1, rx_lon=1,
            tx_h=10, rx_h=5, tx_gain=0, rx_gain=0,
            tx_power_dbm=0, rx_sensitivity_dbm=0,
        )
        write_p2p_marker_layer(
            path=path, tx_lat=2, tx_lon=2, rx_lat=3, rx_lon=3,
            tx_h=20, rx_h=15, tx_gain=1, rx_gain=1,
            tx_power_dbm=10, rx_sensitivity_dbm=-80,
        )
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        assert layer.GetFeatureCount() == 2
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsDouble("latitude") == 2.0
        ds = None


class TestWriteSingleMarker:
    def test_creates_gpkg_with_tx_marker(self, tmp_path):
        path = str(tmp_path / "tx_marker.gpkg")
        result_path = write_single_marker(
            path=path, lat=47.0, lon=8.0,
            height_m=30.0, gain_dbi=5.0, power_dbm=36.0,
            label="TX",
        )
        assert result_path == path
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        assert layer.GetFeatureCount() == 1
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsString("label") == "TX"
        assert feat.GetFieldAsDouble("lat") == 47.0
        assert feat.GetFieldAsDouble("lon") == 8.0
        assert feat.GetFieldAsDouble("h_m") == 30.0
        assert feat.GetFieldAsDouble("gain_dbi") == 5.0
        assert feat.GetFieldAsDouble("pwr_dbm") == 36.0
        ds = None

    def test_null_power_dbm_is_ok(self, tmp_path):
        path = str(tmp_path / "rx_marker.gpkg")
        write_single_marker(
            path=path, lat=47.1, lon=8.1,
            height_m=10.0, gain_dbi=2.0, power_dbm=None,
            label="RX",
        )
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsDouble("pwr_dbm") == 0.0
        ds = None

    def test_geometry_is_point(self, tmp_path):
        path = str(tmp_path / "single.gpkg")
        write_single_marker(
            path=path, lat=47.0, lon=8.0,
            height_m=30.0, gain_dbi=5.0, power_dbm=36.0,
            label="TX",
        )
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        feat = layer.GetNextFeature()
        geom = feat.GetGeometryRef()
        assert geom.GetGeometryName() == "POINT"
        ds = None
