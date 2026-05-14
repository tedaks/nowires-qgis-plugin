# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Contract tests for comparison_params module.

These tests verify structural invariants of the constants defined in
comparison_params. The module uses QGIS-relative imports, so it must be
imported through the NoWires package.
"""

import pytest

pytestmark = pytest.mark.qgis_integration


class TestComparisonParamsConstants:
    def test_panel_a_constants_are_prefixed(self):
        from NoWires.comparison_params import PANEL_A_CONSTANTS
        for key, value in PANEL_A_CONSTANTS.items():
            assert value.startswith("PANEL_A_"), f"{key} -> {value} missing PANEL_A_ prefix"

    def test_panel_b_constants_are_prefixed(self):
        from NoWires.comparison_params import PANEL_B_CONSTANTS
        for key, value in PANEL_B_CONSTANTS.items():
            assert value.startswith("PANEL_B_"), f"{key} -> {value} missing PANEL_B prefix"

    def test_output_constants_have_expected_keys(self):
        from NoWires.comparison_params import OUTPUT_CONSTANTS
        expected = {"OUTPUT_DIR", "DELTA_STYLE", "DELTA_THRESHOLD_DB",
                    "OUTPUT_A", "OUTPUT_B", "OUTPUT_DELTA", "OUTPUT_REPORT_HTML"}
        assert set(OUTPUT_CONSTANTS.keys()) == expected

    def test_delta_style_options_are_valid(self):
        from NoWires.comparison_params import DELTA_STYLE_OPTIONS
        assert "diverging" in DELTA_STYLE_OPTIONS
        assert "threshold" in DELTA_STYLE_OPTIONS

    def test_delta_threshold_defaults_are_positive(self):
        from NoWires.comparison_params import DELTA_THRESHOLD_DEFAULTS
        for t in DELTA_THRESHOLD_DEFAULTS:
            assert t > 0.0

    def test_panel_a_and_b_have_same_keys(self):
        from NoWires.comparison_params import PANEL_A_CONSTANTS, PANEL_B_CONSTANTS
        assert set(PANEL_A_CONSTANTS.keys()) == set(PANEL_B_CONSTANTS.keys())

    def test_panel_keys_contain_expected_fields(self):
        from NoWires.comparison_params import PANEL_A_CONSTANTS
        expected_keys = {"POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ",
                        "RADIUS_KM", "POLARIZATION", "CLIMATE"}
        assert expected_keys.issubset(set(PANEL_A_CONSTANTS.keys()))


class TestMakePanelConfig:
    def test_make_panel_config_returns_expected_keys(self):
        from NoWires.comparison_params import make_panel_config
        config = make_panel_config()
        expected = {"point_param", "height_param", "freq_param", "radius_param",
                    "pct_param", "dbm_param", "gain_param", "db_param",
                    "loss_param", "az_param", "bw_param", "downtilt_param",
                    "n0_param", "epsilon_param", "sigma_param"}
        assert expected.issubset(set(config.keys()))

    def test_height_param_creates_valid_parameter(self):
        from NoWires.comparison_params import make_panel_config
        from qgis.core import QgsProcessingParameterNumber
        config = make_panel_config()
        param = config["height_param"]("PANEL_A_TX_HEIGHT", "TX height", defaultValue=30.0)
        assert isinstance(param, QgsProcessingParameterNumber)
        assert param.name() == "PANEL_A_TX_HEIGHT"

    def test_freq_param_has_bounds(self):
        from NoWires.comparison_params import make_panel_config
        config = make_panel_config()
        param = config["freq_param"]("PANEL_A_FREQ_MHZ", "Frequency", defaultValue=900.0)
        assert param.minimum() > 0
        assert param.maximum() > param.minimum()

    def test_radius_param_has_bounds(self):
        from NoWires.comparison_params import make_panel_config
        config = make_panel_config()
        param = config["radius_param"]("PANEL_A_RADIUS_KM", "Radius", defaultValue=5.0)
        assert param.minimum() >= 1.0
        assert param.maximum() <= 500.0