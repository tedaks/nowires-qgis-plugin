# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for shared_params.py — adding link budget, clutter, and ITM parameters."""


from NoWires.shared_params import (
    add_link_budget_params,
    add_clutter_params,
    add_advanced_itm_params,
    add_advanced_param,
    extract_clutter_params,
)


def _param_name(p):
    return p.name() if callable(p.name) else p.name


def _param_val(p, attr):
    """Access a QGIS parameter attribute, handling method vs property."""
    val = getattr(p, attr)
    return val() if callable(val) else val


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
        assert _param_name(alg.params[0]) == "TX_POWER"
        assert _param_name(alg.params[1]) == "TX_GAIN"
        assert _param_name(alg.params[2]) == "RX_GAIN"
        assert _param_name(alg.params[3]) == "CABLE_LOSS"
        assert _param_name(alg.params[4]) == "RX_SENSITIVITY"


class TestAddClutterParams:
    def test_adds_ten_parameters(self):
        alg = _Alg()
        add_clutter_params(alg)
        assert len(alg.params) == 10

    def test_first_param_is_clutter_model(self):
        alg = _Alg()
        add_clutter_params(alg)
        assert _param_name(alg.params[0]) == "CLUTTER_MODEL"
        assert _param_val(alg.params[0], "defaultValue") == 0

    def test_bel_params_are_present(self):
        alg = _Alg()
        add_clutter_params(alg)
        names = [_param_name(p) for p in alg.params]
        assert "BEL_ENABLED" in names
        assert "BEL_BUILDING_TYPE" in names
        assert "BEL_ELEVATION_ANGLE" in names

    def test_street_width_has_bounds(self):
        alg = _Alg()
        add_clutter_params(alg)
        sw = [p for p in alg.params if _param_name(p) == "STREET_WIDTH"][0]
        assert _param_val(sw, "minimum") == 5.0
        assert _param_val(sw, "maximum") == 100.0


class TestAddAdvancedITMParams:
    def test_adds_k_factor_by_default(self):
        alg = _Alg()
        add_advanced_itm_params(alg)
        names = [_param_name(p) for p in alg.params]
        assert "K_FACTOR_PRESET" in names
        assert "K_FACTOR" in names

    def test_can_exclude_k_factor(self):
        alg = _Alg()
        add_advanced_itm_params(alg, include_k_factor=False)
        names = [_param_name(p) for p in alg.params]
        assert "K_FACTOR_PRESET" not in names
        assert "K_FACTOR" not in names

    def test_always_adds_n0_epsilon_sigma(self):
        alg = _Alg()
        add_advanced_itm_params(alg, include_k_factor=False)
        names = [_param_name(p) for p in alg.params]
        assert "N0" in names
        assert "EPSILON" in names
        assert "SIGMA" in names

    def test_adds_prefix_labels(self):
        alg = _Alg()
        add_advanced_itm_params(alg, prefix="Panel A")
        descs = [p.description if isinstance(p.description, str) else p.description() for p in alg.params]
        assert any("Panel A" in d for d in descs)


class TestAddAdvancedParam:
    def test_creates_number_parameter(self):
        alg = _Alg()
        add_advanced_param(alg, "TEST_PARAM", "Test description", 42.0, min_val=1.0, max_val=100.0)
        assert len(alg.params) == 1
        assert _param_val(alg.params[0], "defaultValue") == 42.0

    def test_optional_params_omitted(self):
        alg = _Alg()
        add_advanced_param(alg, "TEST_PARAM", "Test", 50.0)
        assert len(alg.params) == 1


class _ExtractAlg(_Alg):
    """_Alg variant exposing the parameterAsXxx methods extract_clutter_params calls."""

    def __init__(self, values):
        super().__init__()
        self._values = values

    def parameterAsDouble(self, parameters, name, context):
        return float(self._values[name])

    def parameterAsEnum(self, parameters, name, context):
        return int(self._values[name])

    def parameterAsFile(self, parameters, name, context):
        return str(self._values[name])

    def parameterAsBool(self, parameters, name, context):
        return bool(self._values[name])


def _extract_values(cch_value):
    return {
        "CLUTTER_MODEL": 2,            # advanced
        "CCH_OVERRIDE": cch_value,
        "CLUTTER_RASTER": "",
        "BEL_BUILDING_TYPE": 0,
        "TX_CLUTTER_OVERRIDE": 0,
        "RX_CLUTTER_OVERRIDE": 0,
        "CLUTTER_PERCENTILE": 50.0,
        "STREET_WIDTH": 27.0,
        "BEL_ENABLED": False,
        "BEL_ELEVATION_ANGLE": 0.0,
    }


class TestExtractClutterParamsCchOverride:
    """Regression: UI labels CCH_OVERRIDE as "0 = auto", so 0.0 must become None.

    With cch_override_m=0.0 reaching ``_category_height_m``, every advanced-mode
    pixel short-circuits to zero clutter — silently disabling the model despite a
    valid land-cover grid (observed in field reports: clutter_tx_db /
    clutter_rx_db / bel_rx_db all 0.0, total_path_loss_db == itm_loss_db).
    """

    def test_zero_cch_normalises_to_none(self):
        alg = _ExtractAlg(_extract_values(0.0))
        bundle = extract_clutter_params(alg, parameters={}, context=None)
        assert bundle.cch_override_m is None

    def test_positive_cch_passes_through(self):
        alg = _ExtractAlg(_extract_values(18.0))
        bundle = extract_clutter_params(alg, parameters={}, context=None)
        assert bundle.cch_override_m == 18.0
