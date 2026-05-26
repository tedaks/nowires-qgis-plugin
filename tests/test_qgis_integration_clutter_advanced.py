# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""QGIS integration test: coverage analysis with advanced clutter mode and WorldCover."""

import json
import os
import tempfile

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


@pytest.fixture
def processing_context(qgis_app):
    return QgsProcessingContext()


@pytest.fixture
def feedback():
    return QgsProcessingFeedback()


class TestAdvancedClutterIntegration:
    def test_advanced_clutter_coverage_produces_nonuniform_raster(self, qgis_app):
        from NoWires.algorithm.coverage import CoverageAlgorithm

        alg = CoverageAlgorithm()
        alg.initAlgorithm()

        with tempfile.TemporaryDirectory() as tmpdir:
            params = {
                "TX_POINT": QgsPointXY(121.0, 14.5),
                "TX_HEIGHT": 30.0,
                "RX_HEIGHT": 1.5,
                "FREQ_MHZ": 800.0,
                "RADIUS_KM": 10.0,
                "GRID_SIZE": 0,
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
                "CLUTTER_MODEL": 2,
                "TX_CLUTTER_OVERRIDE": 0,
                "RX_CLUTTER_OVERRIDE": 0,
                "K_FACTOR_PRESET": 2,
                "K_FACTOR": 1.33,
                "N0": 301.0,
                "EPSILON": 15.0,
                "SIGMA": 0.005,
                "OUTPUT_RASTER": os.path.join(tmpdir, "coverage.tif"),
                "OUTPUT_REPORT_JSON": os.path.join(tmpdir, "report.json"),
            }

            context = QgsProcessingContext()
            fb = QgsProcessingFeedback()

            result = alg.processAlgorithm(params, context, fb)

            assert result is not None
            assert "OUTPUT_RASTER" in result

            raster_path = result["OUTPUT_RASTER"]
            from osgeo import gdal
            ds = gdal.Open(raster_path)
            assert ds is not None
            band = ds.GetRasterBand(1)
            data = band.ReadAsArray()
            ds = None

            assert data is not None
            valid = data[~np.isnan(data)]
            assert len(valid) > 0
            assert not np.allclose(valid, valid[0])

            report_path = result.get("OUTPUT_REPORT_JSON")
            if report_path and os.path.exists(report_path):
                with open(report_path, encoding="utf-8") as f:
                    report = json.load(f)
                assert "advanced" in str(report.get("inputs", {}).get("clutter_model", "")).lower()
