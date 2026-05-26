# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validation tests for extract_coverage_params — input validation error paths.

Exercises validation branches in radio_coverage/params.py that are not reached by
the happy-path qgis_integration tests.  Requires QGIS runtime for imports.
"""

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.qgis_integration

from NoWires.radio_coverage.params import extract_coverage_params, PARAM_CONSTANTS
from qgis.core import QgsProcessingException


class _MockAlg:
    """Minimal QgsProcessingAlgorithm mock for extract_coverage_params tests."""

    def __init__(self):
        for k in PARAM_CONSTANTS:
            setattr(self, k, k)

    def parameterAsPoint(self, params, name, context, crs=None):
        return params.get(name)

    def parameterAsDouble(self, params, name, context):
        return params.get(name, 0.0)

    def parameterAsEnum(self, params, name, context):
        return params.get(name, 0)

    def parameterAsBool(self, params, name, context):
        return params.get(name, False)

    def parameterAsFile(self, params, name, context):
        return params.get(name, "")

    def parameterAsInt(self, params, name, context):
        return params.get(name, 0)


def _make_point(lat=14.0, lon=121.0):
    p = MagicMock()
    p.y.return_value = lat
    p.x.return_value = lon
    return p


def _default_params(point=None):
    if point is None:
        point = _make_point()
    return {
        "TX_POINT": point,
        "TX_HEIGHT": 30.0,
        "RX_HEIGHT": 10.0,
        "FREQ_MHZ": 900.0,
        "RADIUS_KM": 5.0,
        "GRID_SIZE": 2,
        "POLARIZATION": 1,
        "CLIMATE": 1,
        "TIME_PCT": 50.0,
        "LOCATION_PCT": 50.0,
        "SITUATION_PCT": 50.0,
        "TX_POWER": 30.0,
        "TX_GAIN": 10.0,
        "RX_GAIN": 8.0,
        "CABLE_LOSS": 1.0,
        "RX_SENSITIVITY": -90.0,
        "ANTENNA_BW": 360.0,
        "ANTENNA_AZ": 0.0,
        "ANTENNA_PRESET": 0,
        "FRONT_BACK_DB": 25.0,
        "DOWNTILT_DEG": 0.0,
        "H_PATTERN": "",
        "V_PATTERN": "",
        "CLUTTER_MODEL": 0,
        "CLUTTER_RASTER": "",
        "TX_CLUTTER_OVERRIDE": 0,
        "RX_CLUTTER_OVERRIDE": 0,
        "CCH_OVERRIDE": 0.0,
        "CLUTTER_PERCENTILE": 50.0,
        "STREET_WIDTH": 27.0,
        "BEL_ENABLED": False,
        "BEL_BUILDING_TYPE": 0,
        "BEL_ELEVATION_ANGLE": 0.0,
        "N0": 301.0,
        "EPSILON": 15.0,
        "SIGMA": 0.005,
    }


class TestCoverageParamsValidation:
    def test_requires_tx_point(self):
        params = _default_params()
        params["TX_POINT"] = None
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"TX point is required\."):
            extract_coverage_params(alg, params, context=None)

    def test_grid_size_exceeds_max(self, monkeypatch):
        from NoWires.radio_coverage import params as cp_params
        monkeypatch.setattr(cp_params, "GRID_SIZE_PRESETS", [2048])
        params = _default_params()
        params["GRID_SIZE"] = 0
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"exceeds maximum \(1024\)"):
            extract_coverage_params(alg, params, context=None)

    def test_radius_zero_raises(self):
        params = _default_params()
        params["RADIUS_KM"] = 0.0
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"Radius must be greater than 0"):
            extract_coverage_params(alg, params, context=None)

    def test_radius_negative_raises(self):
        params = _default_params()
        params["RADIUS_KM"] = -5.0
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"Radius must be greater than 0"):
            extract_coverage_params(alg, params, context=None)

    def test_freq_zero_raises(self):
        params = _default_params()
        params["FREQ_MHZ"] = 0.0
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"Frequency must be greater than 0"):
            extract_coverage_params(alg, params, context=None)

    def test_freq_negative_raises(self):
        params = _default_params()
        params["FREQ_MHZ"] = -10.0
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"Frequency must be greater than 0"):
            extract_coverage_params(alg, params, context=None)

    def test_passes_itm_validation_error_as_qgs_exception(self, monkeypatch):
        from NoWires.radio_coverage import params as cp_params

        def _raise_value_error(*args, **kwargs):
            raise ValueError("TX height out of ITM range [0.5, 3000]")

        monkeypatch.setattr(cp_params, "validate_itm_input_ranges", _raise_value_error)
        params = _default_params()
        alg = _MockAlg()
        with pytest.raises(QgsProcessingException, match=r"TX height out of ITM range"):
            extract_coverage_params(alg, params, context=None)

    def test_extracts_antenna_az_when_beamwidth_lt_360(self):
        params = _default_params()
        params["ANTENNA_PRESET"] = 4
        params["ANTENNA_BW"] = 90.0
        params["ANTENNA_AZ"] = 45.0
        alg = _MockAlg()
        result = extract_coverage_params(alg, params, context=None)
        assert result.antenna_az == 45.0
