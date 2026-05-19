# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for algorithm parameter registration and execution inside QGIS."""

import os
import pytest

try:
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(not _HAS_QGIS, reason="Requires QGIS runtime"),
    pytest.mark.qgis_integration,
]


@pytest.fixture
def processing_context(qgis_app):
    return QgsProcessingContext()


@pytest.fixture
def feedback():
    return QgsProcessingFeedback()


class TestAlgorithmParameterConsistency:
    def test_p2p_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.p2p import P2PAlgorithm
        alg = P2PAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "p2p_analysis"
        params = {p.name() for p in alg.parameterDefinitions()}
        for required in ["TX_POINT", "RX_POINT", "TX_HEIGHT", "RX_HEIGHT",
                         "FREQ_MHZ", "OUTPUT_PROFILE", "OUTPUT_FRESNEL",
                         "OUTPUT_MARKERS"]:
            assert required in params, f"P2P missing param: {required}"

    def test_coverage_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.coverage import CoverageAlgorithm
        alg = CoverageAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "coverage_analysis"
        params = {p.name() for p in alg.parameterDefinitions()}
        for required in ["TX_POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ",
                         "RADIUS_KM", "OUTPUT_RASTER"]:
            assert required in params, f"Coverage missing param: {required}"

    def test_contour_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.contour import ContourLinesAlgorithm
        alg = ContourLinesAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "contour_lines"
        params = {p.name() for p in alg.parameterDefinitions()}
        for required in ["AREA_OF_INTEREST", "INTERVAL", "ELEVATION_MAP"]:
            assert required in params, f"Contour missing param: {required}"

    def test_batch_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm
        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "batch_p2p_analysis"
        params = {p.name() for p in alg.parameterDefinitions()}
        assert "TX_POINT" in params