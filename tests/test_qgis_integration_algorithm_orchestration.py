# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""QGIS integration tests for batch, comparison algorithm orchestration."""

import os

import pytest

try:
    import qgis.core  # noqa: F401
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


class TestBatchAlgorithmIntegration:
    def test_batch_algorithm_registered_in_provider(self, qgis_app):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm
        alg = BatchAnalysisAlgorithm()
        assert alg.name() == "batch_p2p_analysis"
        assert "Batch" in alg.displayName()


class TestComparisonAlgorithmIntegration:
    def test_comparison_algorithm_registered_in_provider(self, qgis_app):
        from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm
        alg = CoverageComparisonAlgorithm()
        assert alg.name() == "coverage_comparison"
        assert "Comparison" in alg.displayName()
