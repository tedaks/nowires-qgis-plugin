# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for comparison/add_params.py — panel and comparison parameter registration."""

import pytest

try:
    from qgis.core import (
        QgsProcessingParameterEnum,
        QgsProcessingParameterFile,
        QgsProcessingParameterFileDestination,
        QgsProcessingParameterFolderDestination,
        QgsProcessingParameterNumber,
        QgsProcessingParameterRasterDestination,
    )
    _HAS_QGIS = bool(__import__("os").environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False


class _FakeAlgorithm:
    def __init__(self):
        self.params = []

    def addParameter(self, param):
        self.params.append(param)

    def parameterDefinitions(self):
        return self.params


@pytest.fixture
def fake_alg():
    return _FakeAlgorithm()


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_panel_params_registers_all_expected(fake_alg):
    from NoWires.comparison.params import make_panel_config
    from NoWires.comparison.add_params import add_panel_params

    config = make_panel_config()
    add_panel_params(fake_alg, "PANEL_A", config)
    param_names = {p.name() for p in fake_alg.params}

    expected = {
        "PANEL_A_POINT", "PANEL_A_TX_HEIGHT", "PANEL_A_RX_HEIGHT",
        "PANEL_A_FREQ_MHZ", "PANEL_A_RADIUS_KM", "PANEL_A_GRID_SIZE",
        "PANEL_A_POLARIZATION", "PANEL_A_CLIMATE", "PANEL_A_TIME_PCT",
        "PANEL_A_LOCATION_PCT", "PANEL_A_SITUATION_PCT",
        "PANEL_A_TX_POWER", "PANEL_A_TX_GAIN", "PANEL_A_RX_GAIN",
        "PANEL_A_CABLE_LOSS", "PANEL_A_RX_SENSITIVITY",
        "PANEL_A_ANTENNA_AZ", "PANEL_A_ANTENNA_BW",
        "PANEL_A_ANTENNA_PRESET", "PANEL_A_FRONT_BACK_DB",
        "PANEL_A_DOWNTILT_DEG", "PANEL_A_H_PATTERN", "PANEL_A_V_PATTERN",
        "PANEL_A_N0", "PANEL_A_EPSILON", "PANEL_A_SIGMA",
    }
    for e in expected:
        assert e in param_names, "Missing param: {}".format(e)


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_panel_b_registers_different_prefix(fake_alg):
    from NoWires.comparison.params import make_panel_config
    from NoWires.comparison.add_params import add_panel_params

    config = make_panel_config()
    add_panel_params(fake_alg, "PANEL_B", config)
    param_names = {p.name() for p in fake_alg.params}

    assert "PANEL_B_POINT" in param_names
    assert "PANEL_B_TX_HEIGHT" in param_names
    assert "PANEL_B_GRID_SIZE" in param_names
    assert not any(p.startswith("PANEL_A_") for p in param_names)


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_comparison_params_registers_all_expected(fake_alg):
    from NoWires.comparison.add_params import add_comparison_params

    add_comparison_params(fake_alg)
    param_names = {p.name() for p in fake_alg.params}
    expected = {
        "OUTPUT_DIR", "DELTA_STYLE", "DELTA_THRESHOLD_DB",
        "OUTPUT_A", "OUTPUT_B", "OUTPUT_DELTA", "OUTPUT_REPORT_HTML",
    }
    assert param_names == expected


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_delta_threshold_has_correct_bounds(fake_alg):
    from NoWires.comparison.add_params import add_comparison_params

    add_comparison_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "DELTA_THRESHOLD_DB")
    assert isinstance(param, QgsProcessingParameterNumber)
    assert param.type() == QgsProcessingParameterNumber.Type.Double
    assert param.minimum() == 0.1
    assert param.defaultValue() == 5.0


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_delta_style_parameter_is_enum_with_options(fake_alg):
    from NoWires.comparison.add_params import add_comparison_params
    from NoWires.comparison.params import DELTA_STYLE_OPTIONS

    add_comparison_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "DELTA_STYLE")
    assert isinstance(param, QgsProcessingParameterEnum)
    assert param.options() == DELTA_STYLE_OPTIONS
    assert param.defaultValue() == 0


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_output_params_are_correct_types(fake_alg):
    from NoWires.comparison.add_params import add_comparison_params

    add_comparison_params(fake_alg)
    name_to_type = {p.name(): type(p) for p in fake_alg.params}

    assert isinstance(name_to_type["OUTPUT_DIR"], QgsProcessingParameterFolderDestination)
    assert isinstance(name_to_type["OUTPUT_A"], QgsProcessingParameterRasterDestination)
    assert isinstance(name_to_type["OUTPUT_B"], QgsProcessingParameterRasterDestination)
    assert isinstance(name_to_type["OUTPUT_DELTA"], QgsProcessingParameterRasterDestination)
    assert isinstance(name_to_type["OUTPUT_REPORT_HTML"], QgsProcessingParameterFileDestination)


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_antenna_pattern_params_are_optional_files(fake_alg):
    from NoWires.comparison.params import make_panel_config
    from NoWires.comparison.add_params import add_panel_params

    config = make_panel_config()
    add_panel_params(fake_alg, "PANEL_A", config)

    h_param = next(p for p in fake_alg.params if p.name() == "PANEL_A_H_PATTERN")
    v_param = next(p for p in fake_alg.params if p.name() == "PANEL_A_V_PATTERN")

    assert isinstance(h_param, QgsProcessingParameterFile)
    assert isinstance(v_param, QgsProcessingParameterFile)
    assert h_param.flags() & QgsProcessingParameterFile.Flag.FlagOptional
    assert v_param.flags() & QgsProcessingParameterFile.Flag.FlagOptional
