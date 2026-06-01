# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Unit tests for comparison_params.collect_panel_params().

The collector reads ~35 QGIS dialog parameters into a ComparisonPanelParams
dataclass. These tests use a fake algorithm object so they run as plain
unit tests (no qgis_integration marker) and lock in:

  * every field of the dataclass is populated from the correct key
  * every key is correctly prefixed
  * derived values (clutter_enabled, clutter_model, bel_building_type,
    cch_override_m, antenna_bw_override) honour their derivation rules
"""

from comparison.params import ComparisonPanelParams, collect_panel_params


class _FakePoint:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class _FakeAlgo:
    """Fake QGIS algorithm that returns values from a {suffix: value} dict.

    Records every (method, key) it was called with so the test can assert
    on the prefixed keys actually requested.
    """
    def __init__(self, values, prefix="PANEL_A", point=None):
        self.values = values
        self.prefix = prefix
        self.point = point if point is not None else _FakePoint(35.5, -120.25)
        self.calls = []

    def _get(self, parameters, key, expected_method):
        self.calls.append((expected_method, key))
        # Strip "<prefix>_" to look up by the bare suffix the test set.
        suffix = key[len(self.prefix) + 1:] if key.startswith(self.prefix + "_") else key
        return self.values[suffix]

    def parameterAsPoint(self, parameters, key, context, crs=None):
        self.calls.append(("Point", key))
        return self.point

    def parameterAsDouble(self, parameters, key, context):
        return self._get(parameters, key, "Double")

    def parameterAsEnum(self, parameters, key, context):
        return self._get(parameters, key, "Enum")

    def parameterAsFile(self, parameters, key, context):
        return self._get(parameters, key, "File")

    def parameterAsBool(self, parameters, key, context):
        return self._get(parameters, key, "Bool")


def _default_values():
    """Distinct values per key so any swap shows up as a wrong-field error."""
    return {
        "TX_HEIGHT": 35.0, "RX_HEIGHT": 2.0,
        "FREQ_MHZ": 2400.0, "RADIUS_KM": 12.5,
        "GRID_SIZE": 2,          # enum index into GRID_SIZE_PRESETS
        "POLARIZATION": 1, "CLIMATE": 3,
        "TIME_PCT": 51.0, "LOCATION_PCT": 52.0, "SITUATION_PCT": 53.0,
        "TX_POWER": 40.0, "TX_GAIN": 12.0,
        "RX_GAIN": 2.5, "CABLE_LOSS": 1.5, "RX_SENSITIVITY": -95.0,
        "ANTENNA_BW": 90.0,      # < 360 → antenna_az is read
        "ANTENNA_AZ": 45.0,
        "ANTENNA_PRESET": 1, "FRONT_BACK_DB": 25.0,
        "DOWNTILT_DEG": 3.0,
        "H_PATTERN": "/tmp/h.csv", "V_PATTERN": "/tmp/v.csv",
        "CLUTTER_MODEL": 2,      # 2 → advanced
        "CCH_OVERRIDE": 18.0,    # > 0 → not None
        "CLUTTER_PERCENTILE": 90.0, "STREET_WIDTH_M": 28.0,
        "BEL_ENABLED": True,
        "BEL_BUILDING_TYPE": 1,  # 1 → thermally_efficient
        "BEL_ELEVATION_ANGLE": 15.0,
        "CLUTTER_RASTER": "/tmp/clutter.tif",
        "TX_CLUTTER_OVERRIDE": 0, "RX_CLUTTER_OVERRIDE": 0,
        "N0": 301.0, "EPSILON": 15.0, "SIGMA": 0.005,
    }


def test_collect_panel_params_returns_dataclass():
    algo = _FakeAlgo(_default_values())
    p = collect_panel_params(algo, "PANEL_A", parameters={}, context=None)
    assert isinstance(p, ComparisonPanelParams)


def test_collect_panel_params_geometry_from_tx_point():
    algo = _FakeAlgo(_default_values(), point=_FakePoint(x=-122.4, y=37.78))
    p = collect_panel_params(algo, "PANEL_A", parameters={}, context=None)
    assert p.tx_lat == 37.78  # point.y()
    assert p.tx_lon == -122.4  # point.x()


def test_collect_panel_params_simple_field_mapping():
    algo = _FakeAlgo(_default_values())
    p = collect_panel_params(algo, "PANEL_A", parameters={}, context=None)
    # Every distinct value should land in its named field.
    assert p.tx_h == 35.0
    assert p.rx_h == 2.0
    assert p.f_mhz == 2400.0
    assert p.radius_km == 12.5
    assert p.polarization == 1
    assert p.climate == 3
    assert p.time_pct == 51.0
    assert p.location_pct == 52.0
    assert p.situation_pct == 53.0
    assert p.tx_power == 40.0
    assert p.tx_gain == 12.0
    assert p.rx_gain == 2.5
    assert p.cable_loss == 1.5
    assert p.rx_sens == -95.0
    assert p.antenna_bw == 90.0
    assert p.antenna_preset == 1
    assert p.front_back_db == 25.0
    assert p.downtilt_deg == 3.0
    assert p.h_pattern == "/tmp/h.csv"
    assert p.v_pattern == "/tmp/v.csv"
    assert p.clutter_percentile == 90.0
    assert p.street_width_m == 28.0
    assert p.bel_enabled is True
    assert p.bel_elevation_angle_deg == 15.0
    assert p.clutter_raster_path == "/tmp/clutter.tif"
    assert p.n0 == 301.0
    assert p.epsilon == 15.0
    assert p.sigma == 0.005


def test_collect_panel_params_grid_size_maps_through_presets():
    from comparison.params import GRID_SIZE_PRESETS
    algo = _FakeAlgo(_default_values())
    p = collect_panel_params(algo, "PANEL_A", parameters={}, context=None)
    assert p.grid_size == GRID_SIZE_PRESETS[2]


def test_collect_panel_params_clutter_model_derivation():
    # 0 → disabled, 1 → simple, 2 → advanced
    for idx, expected_enabled, expected_model in (
        (0, False, "simple"),
        (1, True, "simple"),
        (2, True, "advanced"),
    ):
        v = _default_values()
        v["CLUTTER_MODEL"] = idx
        p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
        assert p.clutter_enabled is expected_enabled, f"idx={idx}"
        assert p.clutter_model == expected_model, f"idx={idx}"


def test_collect_panel_params_cch_override_zero_becomes_none():
    v = _default_values()
    v["CCH_OVERRIDE"] = 0.0
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.cch_override_m is None


def test_collect_panel_params_cch_override_negative_becomes_none():
    v = _default_values()
    v["CCH_OVERRIDE"] = -1.0
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.cch_override_m is None


def test_collect_panel_params_cch_override_positive_preserved():
    v = _default_values()
    v["CCH_OVERRIDE"] = 18.0
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.cch_override_m == 18.0


def test_collect_panel_params_bel_building_type_derivation():
    v = _default_values()
    v["BEL_BUILDING_TYPE"] = 0
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.bel_building_type == "traditional"

    v["BEL_BUILDING_TYPE"] = 1
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.bel_building_type == "thermally_efficient"


def test_collect_panel_params_antenna_az_only_read_when_bw_lt_360():
    v = _default_values()
    v["ANTENNA_BW"] = 360.0
    # If antenna_az were read, the missing/wrong key would land in calls;
    # asserting on the result is enough — antenna_az should be None.
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.antenna_az is None

    v["ANTENNA_BW"] = 90.0
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.antenna_az == 45.0


def test_collect_panel_params_antenna_bw_override_rule():
    # Rule: PRESET=0 (omni) forces AZ=None and BW=360 regardless of raw BW.
    from comparison.params import CUSTOM_ANTENNA_PRESET_INDEX

    # Case A: bw == 360, preset == omni → override 360, az None.
    v = _default_values()
    v["ANTENNA_BW"] = 360.0
    v["ANTENNA_PRESET"] = 0  # omni
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.antenna_bw_override == 360.0
    assert p.antenna_az is None

    # Case B: bw == 360, preset == custom → override == bw.
    v["ANTENNA_PRESET"] = CUSTOM_ANTENNA_PRESET_INDEX
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.antenna_bw_override == 360.0

    # Case C: bw < 360, preset == omni → override 360, az None.
    v["ANTENNA_BW"] = 90.0
    v["ANTENNA_PRESET"] = 0
    p = collect_panel_params(_FakeAlgo(v), "PANEL_A", parameters={}, context=None)
    assert p.antenna_bw_override == 360.0
    assert p.antenna_az is None


def test_collect_panel_params_prefixes_every_key():
    algo = _FakeAlgo(_default_values(), prefix="PANEL_B")
    collect_panel_params(algo, "PANEL_B", parameters={}, context=None)
    for _method, key in algo.calls:
        assert key.startswith("PANEL_B_"), f"unprefixed key requested: {key}"


def test_collect_panel_params_raises_on_missing_tx_point():
    algo = _FakeAlgo(_default_values(), point=None)
    # Manually drop the point so parameterAsPoint returns None.
    algo.point = None
    import pytest
    with pytest.raises(ValueError, match="TX point is required"):
        collect_panel_params(algo, "PANEL_A", parameters={}, context=None)
