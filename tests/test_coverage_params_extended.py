# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for coverage_params.py — extract_coverage_params and add_coverage_params."""


from NoWires.radio_coverage.params import (
    extract_coverage_params,
    add_coverage_params,
    PARAM_CONSTANTS,
)
from NoWires.radio_coverage.analysis_params import CoverageAnalysisParams


def _pname(p):
    val = getattr(p, "name")
    return val() if callable(val) else val


class _Alg:
    def __init__(self):
        self._params = {}
        self._added = []
        for k, v in PARAM_CONSTANTS.items():
            setattr(self, k, k)

    def addParameter(self, param):
        self._added.append(param)

    def parameterAsPoint(self, params, name, context, crs=None):
        return self._params.get(name)

    def parameterAsDouble(self, params, name, context):
        return self._params.get(name, 0.0)

    def parameterAsEnum(self, params, name, context):
        return self._params.get(name, 0)

    def parameterAsBool(self, params, name, context):
        return self._params.get(name, False)

    def parameterAsFile(self, params, name, context):
        return self._params.get(name, "")

    def parameterAsInt(self, params, name, context):
        return self._params.get(name, 0)


class TestAddCoverageParams:
    def test_adds_parameters(self):
        alg = _Alg()
        add_coverage_params(alg)
        assert len(alg._added) > 10

    def test_tx_point_param_is_point_type(self):
        alg = _Alg()
        add_coverage_params(alg)
        point_params = [p for p in alg._added if _pname(p) == "TX_POINT"]
        assert len(point_params) == 1

    def test_grid_size_is_enum(self):
        alg = _Alg()
        add_coverage_params(alg)
        gs = [p for p in alg._added if _pname(p) == "GRID_SIZE"]
        assert len(gs) == 1
        assert hasattr(gs[0], "options")


class TestExtractCoverageParams:
    def test_extracts_with_defaults(self, monkeypatch):
        from unittest.mock import MagicMock
        alg = _Alg()
        point = MagicMock()
        point.y.return_value = 14.0
        point.x.return_value = 121.0
        params = {
            "TX_POINT": point, "TX_HEIGHT": 30.0, "RX_HEIGHT": 10.0,
            "FREQ_MHZ": 900.0, "RADIUS_KM": 5.0, "GRID_SIZE": 0,
            "POLARIZATION": 1, "CLIMATE": 1, "TIME_PCT": 50.0,
            "LOCATION_PCT": 50.0, "SITUATION_PCT": 50.0,
            "TX_POWER": 30.0, "TX_GAIN": 10.0, "RX_GAIN": 8.0,
            "CABLE_LOSS": 1.0, "RX_SENSITIVITY": -90.0,
            "ANTENNA_BW": 360.0, "ANTENNA_AZ": 0.0, "ANTENNA_PRESET": 0,
            "FRONT_BACK_DB": 25.0, "DOWNTILT_DEG": 0.0, "H_PATTERN": "",
            "V_PATTERN": "", "CLUTTER_MODEL": 0, "CLUTTER_RASTER": "",
            "TX_CLUTTER_OVERRIDE": 0, "RX_CLUTTER_OVERRIDE": 0,
            "CCH_OVERRIDE": 0.0, "CLUTTER_PERCENTILE": 50.0,
            "STREET_WIDTH": 27.0, "BEL_ENABLED": False, "BEL_BUILDING_TYPE": 0,
            "BEL_ELEVATION_ANGLE": 0.0,
            "N0": 301.0, "EPSILON": 15.0, "SIGMA": 0.005,
        }
        alg._params = params

        result = extract_coverage_params(alg, params, context=None)
        assert isinstance(result, CoverageAnalysisParams)
        assert result.tx_lat == 14.0
        assert result.tx_lon == 121.0
        assert result.tx_h == 30.0
        assert result.radius_km == 5.0
