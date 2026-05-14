# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Contract tests for coverage_params module constants.

Requires QGIS runtime for import.
"""

import pytest

pytestmark = pytest.mark.qgis_integration


class TestCoverageParamsConstants:
    def test_param_constants_contains_expected_keys(self):
        from NoWires.coverage_params import PARAM_CONSTANTS
        expected = {
            "TX_POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "RADIUS_KM",
            "GRID_SIZE", "POLARIZATION", "CLIMATE", "TIME_PCT",
            "LOCATION_PCT", "SITUATION_PCT", "TX_POWER", "TX_GAIN",
            "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY", "ANTENNA_BW",
            "ANTENNA_AZ", "ANTENNA_PRESET", "FRONT_BACK_DB", "DOWNTILT_DEG",
            "H_PATTERN", "V_PATTERN", "CLUTTER_MODEL", "CLUTTER_RASTER",
            "TX_CLUTTER_OVERRIDE", "RX_CLUTTER_OVERRIDE", "CCH_OVERRIDE",
            "OUTPUT_RASTER", "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON",
            "OUTPUT_REPORT_HTML",
        }
        assert expected.issubset(set(PARAM_CONSTANTS.keys()))

    def test_param_constants_values_match_keys(self):
        from NoWires.coverage_params import PARAM_CONSTANTS
        for key, value in PARAM_CONSTANTS.items():
            assert value == key, f"PARAM_CONSTANTS[{key!r}] = {value!r}, expected {key!r}"