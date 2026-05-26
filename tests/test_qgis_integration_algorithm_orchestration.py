# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""QGIS integration tests for batch, comparison, contour algorithm orchestration."""

import os

import numpy as np
import pytest

try:
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsPointXY
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
    def test_batch_algorithm_registers_and_accepts_params(self, qgis_app):
        from NoWires.algorithm.batch import BatchP2PAlgorithm
        alg = BatchP2PAlgorithm()
        alg.initAlgorithm()
        assert alg.name() == "batch_p2p"
        assert "Point" in alg.displayName() or "Batch" in alg.displayName()

    def test_batch_one_to_many_with_valid_points(self, qgis_app):
        from NoWires.algorithm.batch import BatchP2PAlgorithm
        import tempfile

        alg = BatchP2PAlgorithm()
        alg.initAlgorithm()

        with tempfile.TemporaryDirectory() as tmpdir:
            params = {
                "TX_POINT": QgsPointXY(121.0, 14.5),
                "TX_HEIGHT": 30.0,
                "RX_POINTS": QgsPointXY(121.05, 14.55),
                "FREQ_MHZ": 900.0,
                "POLARIZATION": 1,
                "CLIMATE": 1,
                "TIME_PCT": 50.0,
                "LOCATION_PCT": 50.0,
                "SITUATION_PCT": 50.0,
                "TX_POWER": 40.0,
                "TX_GAIN": 10.0,
                "RX_GAIN": 0.0,
                "CABLE_LOSS": 1.0,
                "RX_SENS": -95.0,
                "ANTENNA_PRESET": 0,
                "FRONT_BACK_DB": 25.0,
                "DOWNTILT_DEG": 0.0,
                "CLUTTER_MODEL": 0,
                "K_FACTOR_PRESET": 2,
                "N0": 301.0,
                "EPSILON": 15.0,
                "SIGMA": 0.005,
                "OUTPUT_RESULTS": os.path.join(tmpdir, "results.gpkg"),
            }
            context = QgsProcessingContext()
            fb = QgsProcessingFeedback()
            result = alg.processAlgorithm(params, context, fb)
            assert result is not None
            assert "OUTPUT_RESULTS" in result


class TestComparisonAlgorithmIntegration:
    def test_comparison_algorithm_registers_and_accepts_params(self, qgis_app):
        from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm
        alg = CoverageComparisonAlgorithm()
        alg.initAlgorithm()
        assert alg.name() == "coverage_comparison"
        assert "Comparison" in alg.displayName()

    def test_comparison_with_valid_params(self, qgis_app):
        from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm
        import tempfile

        alg = CoverageComparisonAlgorithm()
        alg.initAlgorithm()

        with tempfile.TemporaryDirectory() as tmpdir:
            params = {
                "TX_POINT_A": QgsPointXY(121.0, 14.5),
                "TX_POINT_B": QgsPointXY(121.0, 14.5),
                "TX_HEIGHT_A": 30.0,
                "TX_HEIGHT_B": 30.0,
                "RX_HEIGHT_A": 1.5,
                "RX_HEIGHT_B": 1.5,
                "FREQ_MHZ_A": 900.0,
                "FREQ_MHZ_B": 900.0,
                "RADIUS_KM_A": 5.0,
                "RADIUS_KM_B": 5.0,
                "GRID_SIZE_A": 0,
                "GRID_SIZE_B": 0,
                "POLARIZATION_A": 1,
                "POLARIZATION_B": 1,
                "CLIMATE_A": 1,
                "CLIMATE_B": 1,
                "TIME_PCT_A": 50.0,
                "TIME_PCT_B": 50.0,
                "LOCATION_PCT_A": 50.0,
                "LOCATION_PCT_B": 50.0,
                "SITUATION_PCT_A": 50.0,
                "SITUATION_PCT_B": 50.0,
                "TX_POWER_A": 40.0,
                "TX_POWER_B": 40.0,
                "TX_GAIN_A": 10.0,
                "TX_GAIN_B": 10.0,
                "RX_GAIN_A": 0.0,
                "RX_GAIN_B": 0.0,
                "CABLE_LOSS_A": 1.0,
                "CABLE_LOSS_B": 1.0,
                "RX_SENS_A": -95.0,
                "RX_SENS_B": -95.0,
                "ANTENNA_PRESET_A": 0,
                "ANTENNA_PRESET_B": 0,
                "FRONT_BACK_DB_A": 25.0,
                "FRONT_BACK_DB_B": 25.0,
                "DOWNTILT_DEG_A": 0.0,
                "DOWNTILT_DEG_B": 0.0,
                "CLUTTER_MODEL_A": 0,
                "CLUTTER_MODEL_B": 0,
                "K_FACTOR_PRESET_A": 2,
                "K_FACTOR_PRESET_B": 2,
                "N0_A": 301.0, "N0_B": 301.0,
                "EPSILON_A": 15.0, "EPSILON_B": 15.0,
                "SIGMA_A": 0.005, "SIGMA_B": 0.005,
                "OUTPUT_DELTA": os.path.join(tmpdir, "delta.tif"),
            }
            context = QgsProcessingContext()
            fb = QgsProcessingFeedback()
            result = alg.processAlgorithm(params, context, fb)
            assert result is not None
            assert "OUTPUT_DELTA" in result


class TestContourAlgorithmIntegration:
    def test_contour_algorithm_registers_and_accepts_params(self, qgis_app):
        from NoWires.algorithm.contour import ContourAlgorithm
        alg = ContourAlgorithm()
        alg.initAlgorithm()
        assert alg.name() == "contour_lines"
        assert "Contour" in alg.displayName()
