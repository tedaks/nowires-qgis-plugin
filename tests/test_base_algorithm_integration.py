# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Integration tests for base_algorithm.py postProcess."""

import os
import pytest

try:
    from qgis.core import QgsProject, QgsProcessingContext, QgsProcessingFeedback, Qgis
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(not _HAS_QGIS, reason="Requires QGIS runtime"),
    pytest.mark.qgis_integration,
]


class TestNoWiresAlgorithmFlags:
    def test_algorithm_has_no_threading_flag(self, qgis_app):
        from NoWires.base_algorithm import NoWiresAlgorithm
        alg = NoWiresAlgorithm()
        assert alg.flags() & Qgis.ProcessingAlgorithmFlag.NoThreading

    def test_group_id(self, qgis_app):
        from NoWires.base_algorithm import NoWiresAlgorithm
        alg = NoWiresAlgorithm()
        assert alg.groupId() == "radio_propagation"

    def test_tr_returns_string(self, qgis_app):
        from NoWires.base_algorithm import NoWiresAlgorithm
        alg = NoWiresAlgorithm()
        assert isinstance(alg.tr("test"), str)


class TestPostProcessAlgorithm:
    def test_postprocess_writes_project_entries(self, qgis_app):
        from NoWires.base_algorithm import (
            NoWiresAlgorithm, ENTRY_KEY_LAST_DEM, ENTRY_KEY_LAST_COVERAGE,
        )
        alg = NoWiresAlgorithm()
        alg._dem_layer_id = "test_dem_id_123"
        alg._coverage_layer_id = "test_cov_id_456"
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        result = alg.postProcessAlgorithm(context, feedback)
        assert isinstance(result, dict)
        project = QgsProject.instance()
        dem_val = project.readEntry("NoWires", ENTRY_KEY_LAST_DEM)
        assert dem_val[0] == "test_dem_id_123"
        cov_val = project.readEntry("NoWires", ENTRY_KEY_LAST_COVERAGE)
        assert cov_val[0] == "test_cov_id_456"

    def test_postprocess_handles_missing_ids(self, qgis_app):
        from NoWires.base_algorithm import NoWiresAlgorithm
        alg = NoWiresAlgorithm()
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        result = alg.postProcessAlgorithm(context, feedback)
        assert isinstance(result, dict)