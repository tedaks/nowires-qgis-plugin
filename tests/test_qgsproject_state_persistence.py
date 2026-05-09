# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify QgsProject state persistence used by NoWires algorithms."""

import os
import pytest

try:
    from qgis.core import QgsProject
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


class TestQgsProjectStatePersistence:
    def test_write_and_read_entry(self, qgis_app):
        project = QgsProject.instance()
        project.writeEntry("NoWires", "last_dem_layer_id", "test_dem_id_123")
        result, ok = project.readEntry("NoWires", "last_dem_layer_id", "")
        assert ok
        assert result == "test_dem_id_123"

    def test_write_and_read_coverage_layer_id(self, qgis_app):
        project = QgsProject.instance()
        project.writeEntry("NoWires", "last_coverage_layer_id", "test_cov_id_456")
        result, ok = project.readEntry("NoWires", "last_coverage_layer_id", "")
        assert ok
        assert result == "test_cov_id_456"

    def test_write_and_read_contour_layer_id(self, qgis_app):
        project = QgsProject.instance()
        project.writeEntry("NoWires", "last_contour_layer_id", "test_contour_id_789")
        result, ok = project.readEntry("NoWires", "last_contour_layer_id", "")
        assert ok
        assert result == "test_contour_id_789"

    def test_layer_tree_root_accessible(self, qgis_app):
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        assert root is not None

    def test_read_nonexistent_entry_returns_default(self, qgis_app):
        project = QgsProject.instance()
        result, ok = project.readEntry("NoWires", "nonexistent_key", "default_val")
        assert not ok
        assert result == "default_val"

    def test_base_algorithm_post_process_writes_entries(self, qgis_app):
        from NoWires.base_algorithm import ENTRY_KEY_LAST_DEM, ENTRY_KEY_LAST_COVERAGE
        alg = type("TestAlg", (), {
            "_raster_layer_ids": ["layer_1", "layer_2"],
            "_dem_layer_id": "dem_layer_id",
            "_coverage_layer_id": "coverage_layer_id",
        })()
        project = QgsProject.instance()
        project.writeEntry("NoWires", ENTRY_KEY_LAST_DEM, alg._dem_layer_id)
        project.writeEntry("NoWires", ENTRY_KEY_LAST_COVERAGE, alg._coverage_layer_id)
        result_dem, _ = project.readEntry("NoWires", ENTRY_KEY_LAST_DEM, "")
        result_cov, _ = project.readEntry("NoWires", ENTRY_KEY_LAST_COVERAGE, "")
        assert result_dem == "dem_layer_id"
        assert result_cov == "coverage_layer_id"