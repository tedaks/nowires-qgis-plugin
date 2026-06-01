# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test: Omni preset forces beamwidth 360 and azimuth None in comparison params.

When ANTENNA_PRESET=0 (Omni), collect_panel_params must override any custom
ANTENNA_BW/ANTENNA_AZ values with 360.0 and None respectively, preventing
downstream confusion where the Omni preset is treated as authoritative but the
custom beamwidth survives.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.qgis_integration


def _build_mock_algo(overrides):
    """Build a MagicMock algorithm whose parameterAs* methods return overridden values."""

    defaults = {
        "ANTENNA_PRESET": 0,
        "ANTENNA_BW": 120.0,
        "ANTENNA_AZ": 135.0,
        "TX_HEIGHT": 30.0,
        "RX_HEIGHT": 10.0,
        "FREQ_MHZ": 900.0,
        "RADIUS_KM": 5.0,
        "GRID_SIZE": 2,
        "POLARIZATION": 0,
        "CLIMATE": 1,
        "TIME_PCT": 50.0,
        "LOCATION_PCT": 50.0,
        "SITUATION_PCT": 50.0,
        "TX_POWER": 43.0,
        "TX_GAIN": 8.0,
        "RX_GAIN": 2.0,
        "CABLE_LOSS": 2.0,
        "RX_SENSITIVITY": -90.0,
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
        "STREET_WIDTH_M": 27.0,
        "BEL_ENABLED": False,
        "BEL_BUILDING_TYPE": 0,
        "BEL_ELEVATION_ANGLE": 30.0,
        "N0": 301.0,
        "EPSILON": 15.0,
        "SIGMA": 0.005,
    }
    defaults.update(overrides)

    algo = MagicMock()

    def _param_d(parameters, key, context):
        return float(defaults.get(key.split("_", 2)[2] if key.startswith("PANEL_") else key, 0.0))

    def _param_e(parameters, key, context):
        return int(defaults.get(key.split("_", 2)[2] if key.startswith("PANEL_") else key, 0))

    def _param_f(parameters, key, context):
        return str(defaults.get(key.split("_", 2)[2] if key.startswith("PANEL_") else key, ""))

    def _param_b(parameters, key, context):
        return bool(defaults.get(key.split("_", 2)[2] if key.startswith("PANEL_") else key, False))

    from qgis.core import QgsPointXY
    algo.parameterAsPoint.side_effect = lambda p, k, c, crs: QgsPointXY(121.0, 14.0)
    algo.parameterAsDouble.side_effect = _param_d
    algo.parameterAsEnum.side_effect = _param_e
    algo.parameterAsFile.side_effect = _param_f
    algo.parameterAsBool.side_effect = _param_b

    return algo


def test_omni_preset_overrides_custom_bw_and_az():
    """Omni preset forces bw_override=360.0 and az=None despite custom values."""
    from NoWires.comparison.params import collect_panel_params

    algo = _build_mock_algo({"ANTENNA_PRESET": 0, "ANTENNA_BW": 120.0, "ANTENNA_AZ": 135.0})

    params = collect_panel_params(
        algo=algo, prefix="PANEL_A",
        parameters={}, context=MagicMock(),
    )

    assert params.antenna_bw_override == 360.0, (
        "Omni preset must force antenna_bw_override=360.0, "
        "got %s" % params.antenna_bw_override
    )
    assert params.antenna_az is None, (
        "Omni preset must force antenna_az=None, got %s" % params.antenna_az
    )


def test_non_omni_preset_respects_custom_bw():
    """Non-Omni preset with custom BW preserves the override."""
    from NoWires.antenna import CUSTOM_ANTENNA_PRESET_INDEX
    from NoWires.comparison.params import collect_panel_params

    algo = _build_mock_algo({
        "ANTENNA_PRESET": CUSTOM_ANTENNA_PRESET_INDEX,
        "ANTENNA_BW": 120.0,
        "ANTENNA_AZ": 90.0,
    })

    params = collect_panel_params(
        algo=algo, prefix="PANEL_A",
        parameters={}, context=MagicMock(),
    )

    assert params.antenna_bw_override == 120.0
    assert params.antenna_az == 90.0
