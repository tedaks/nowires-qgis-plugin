# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify batch marker layer GPKG loads correctly in QGIS."""

import os
import pytest

try:
    from qgis.core import QgsVectorLayer, QgsWkbTypes
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(
        not _HAS_QGIS,
        reason="QGIS integration tests require QGIS_PREFIX_PATH to be set",
    ),
    pytest.mark.qgis_integration,
]


class TestBatchMarkerLayer:
    def test_marker_layer_loads_in_qgis(self, qgis_app, tmp_path):
        from NoWires.batch.writer import write_batch_marker_layer
        gpkg = str(tmp_path / "batch_markers.gpkg")
        results = [
            {"tx_lat": 47.0, "tx_lon": 8.0, "rx_lat": 47.05, "rx_lon": 8.05,
             "dist_m": 5500.0, "dist_km": 5.5, "itm_loss_db": 110.0,
             "total_loss_db": 115.0, "prx_dbm": -50.0, "margin_db": 10.0,
             "clearance_pct": 95.0, "status": "VIABLE",
             "tx_height": 30.0, "rx_height": 10.0},
            {"tx_lat": 47.0, "tx_lon": 8.0, "rx_lat": 47.1, "rx_lon": 8.1,
             "dist_m": 12000.0, "dist_km": 12.0, "itm_loss_db": 140.0,
             "total_loss_db": 150.0, "prx_dbm": -80.0, "margin_db": -20.0,
             "clearance_pct": 30.0, "status": "NOT VIABLE",
             "tx_height": 30.0, "rx_height": 10.0},
        ]
        from unittest.mock import MagicMock
        feedback = MagicMock()
        write_batch_marker_layer(gpkg, results, feedback, mode=0)
        layer = QgsVectorLayer(gpkg, "batch_markers", "ogr")
        assert layer.isValid(), "Batch marker GPKG did not load: {}".format(
            "layer load failed")

    def test_marker_layer_feature_count(self, qgis_app, tmp_path):
        from NoWires.batch.writer import write_batch_marker_layer
        gpkg = str(tmp_path / "batch_count.gpkg")
        results = [
            {"tx_lat": 47.0, "tx_lon": 8.0, "rx_lat": 47.05, "rx_lon": 8.05,
             "dist_m": 5500.0, "dist_km": 5.5, "itm_loss_db": 110.0,
             "total_loss_db": 115.0, "prx_dbm": -50.0, "margin_db": 10.0,
             "clearance_pct": 95.0, "status": "VIABLE",
             "tx_height": 30.0, "rx_height": 10.0},
        ]
        from unittest.mock import MagicMock
        feedback = MagicMock()
        write_batch_marker_layer(gpkg, results, feedback, mode=0)
        layer = QgsVectorLayer(gpkg, "batch_count", "ogr")
        assert layer.isValid()
        assert layer.featureCount() == 1

    def test_marker_layer_has_expected_fields(self, qgis_app, tmp_path):
        from NoWires.batch.writer import write_batch_marker_layer
        gpkg = str(tmp_path / "batch_fields.gpkg")
        results = [
            {"tx_lat": 47.0, "tx_lon": 8.0, "rx_lat": 47.05, "rx_lon": 8.05,
             "dist_m": 5500.0, "dist_km": 5.5, "itm_loss_db": 110.0,
             "total_loss_db": 115.0, "prx_dbm": -50.0, "margin_db": 10.0,
             "clearance_pct": 95.0, "status": "VIABLE",
             "tx_height": 30.0, "rx_height": 10.0},
        ]
        from unittest.mock import MagicMock
        feedback = MagicMock()
        write_batch_marker_layer(gpkg, results, feedback, mode=0)
        layer = QgsVectorLayer(gpkg, "batch_fields", "ogr")
        assert layer.isValid()
        expected_fields = ["rank", "point_id", "margin_db", "dist_km", "status"]
        field_names = [f.name() for f in layer.fields()]
        for name in expected_fields:
            assert name in field_names, "Missing field: {}".format(name)

    def test_marker_layer_is_point_geometry(self, qgis_app, tmp_path):
        from NoWires.batch.writer import write_batch_marker_layer
        gpkg = str(tmp_path / "batch_geom.gpkg")
        results = [
            {"tx_lat": 47.0, "tx_lon": 8.0, "rx_lat": 47.05, "rx_lon": 8.05,
             "dist_m": 5500.0, "dist_km": 5.5, "itm_loss_db": 110.0,
             "total_loss_db": 115.0, "prx_dbm": -50.0, "margin_db": 10.0,
             "clearance_pct": 95.0, "status": "VIABLE",
             "tx_height": 30.0, "rx_height": 10.0},
        ]
        from unittest.mock import MagicMock
        feedback = MagicMock()
        write_batch_marker_layer(gpkg, results, feedback, mode=0)
        layer = QgsVectorLayer(gpkg, "batch_geom", "ogr")
        assert layer.isValid()
        wkb = layer.wkbType()
        assert QgsWkbTypes.flatType(wkb) == QgsWkbTypes.Type.Point