# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for shared_params.py — adding link budget, clutter, and ITM parameters."""


from NoWires.shared_params import (
    add_link_budget_params,
    add_clutter_params,
    add_advanced_itm_params,
    add_advanced_param,
)


class _Alg:
    def __init__(self):
        self.params = []
        self.TX_POWER = "TX_POWER"
        self.TX_GAIN = "TX_GAIN"
        self.RX_GAIN = "RX_GAIN"
        self.CABLE_LOSS = "CABLE_LOSS"
        self.RX_SENSITIVITY = "RX_SENSITIVITY"
        self.CLUTTER_MODEL = "CLUTTER_MODEL"
        self.CLUTTER_RASTER = "CLUTTER_RASTER"
        self.TX_CLUTTER_OVERRIDE = "TX_CLUTTER_OVERRIDE"
        self.RX_CLUTTER_OVERRIDE = "RX_CLUTTER_OVERRIDE"
        self.CCH_OVERRIDE = "CCH_OVERRIDE"
        self.CLUTTER_PERCENTILE = "CLUTTER_PERCENTILE"
        self.STREET_WIDTH = "STREET_WIDTH"
        self.BEL_ENABLED = "BEL_ENABLED"
        self.BEL_BUILDING_TYPE = "BEL_BUILDING_TYPE"
        self.BEL_ELEVATION_ANGLE = "BEL_ELEVATION_ANGLE"
        self.K_FACTOR_PRESET = "K_FACTOR_PRESET"
        self.K_FACTOR = "K_FACTOR"
        self.N0 = "N0"
        self.EPSILON = "EPSILON"
        self.SIGMA = "SIGMA"

    def addParameter(self, param):
        self.params.append(param)


class TestAddLinkBudgetParams:
    def test_adds_five_parameters(self):
        alg = _Alg()
        add_link_budget_params(alg)
        assert len(alg.params) == 5

    def test_adds_parameters_with_expected_order(self):
        alg = _Alg()
        add_link_budget_params(alg)
        assert alg.params[0].name == "TX_POWER"
        assert alg.params[1].name == "TX_GAIN"
        assert alg.params[2].name == "RX_GAIN"
        assert alg.params[3].name == "CABLE_LOSS"
        assert alg.params[4].name == "RX_SENSITIVITY"


class TestAddClutterParams:
    def test_adds_ten_parameters(self):
        alg = _Alg()
        add_clutter_params(alg)
        assert len(alg.params) == 10

    def test_first_param_is_clutter_model(self):
        alg = _Alg()
        add_clutter_params(alg)
        assert alg.params[0].name == "CLUTTER_MODEL"
        assert alg.params[0].defaultValue == 0

    def test_bel_params_are_present(self):
        alg = _Alg()
        add_clutter_params(alg)
        names = [p.name for p in alg.params]
        assert "BEL_ENABLED" in names
        assert "BEL_BUILDING_TYPE" in names
        assert "BEL_ELEVATION_ANGLE" in names

    def test_street_width_has_bounds(self):
        alg = _Alg()
        add_clutter_params(alg)
        sw = [p for p in alg.params if p.name == "STREET_WIDTH"][0]
        assert sw.minValue == 5.0
        assert sw.maxValue == 100.0


class TestAddAdvancedITMParams:
    def test_adds_k_factor_by_default(self):
        alg = _Alg()
        add_advanced_itm_params(alg)
        names = [p.name for p in alg.params]
        assert "K_FACTOR_PRESET" in names
        assert "K_FACTOR" in names

    def test_can_exclude_k_factor(self):
        alg = _Alg()
        add_advanced_itm_params(alg, include_k_factor=False)
        names = [p.name for p in alg.params]
        assert "K_FACTOR_PRESET" not in names
        assert "K_FACTOR" not in names

    def test_always_adds_n0_epsilon_sigma(self):
        alg = _Alg()
        add_advanced_itm_params(alg, include_k_factor=False)
        names = [p.name for p in alg.params]
        assert "N0" in names
        assert "EPSILON" in names
        assert "SIGMA" in names

    def test_adds_prefix_labels(self):
        alg = _Alg()
        add_advanced_itm_params(alg, prefix="Panel A")
        labels = [p.description for p in alg.params]
        assert any("Panel A" in label for label in labels)


class TestAddAdvancedParam:
    def test_creates_number_parameter(self):
        alg = _Alg()
        add_advanced_param(alg, "TEST_PARAM", "Test description", 42.0, min_val=1.0, max_val=100.0)
        assert len(alg.params) == 1
        assert alg.params[0].defaultValue == 42.0

    def test_optional_params_omitted(self):
        alg = _Alg()
        add_advanced_param(alg, "TEST_PARAM", "Test", 50.0)
        assert len(alg.params) == 1
