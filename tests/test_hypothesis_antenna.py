# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Property-based tests for antenna.py using hypothesis."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from antenna import (
    antenna_gain_factor,
    antenna_config_from_values,
    ANTENNA_PRESET_KEYS,
    _angle_diff_deg,
)


class TestAngleDiffProperties:
    @given(a=st.floats(min_value=-720, max_value=720), b=st.floats(min_value=-720, max_value=720))
    @settings(max_examples=100)
    def test_angle_diff_is_in_range(self, a, b):
        diff = _angle_diff_deg(a, b)
        assert -180.0 <= diff <= 180.0

    @given(a=st.floats(min_value=-360, max_value=360))
    @settings(max_examples=50)
    def test_angle_diff_self_is_zero(self, a):
        diff = _angle_diff_deg(a, a)
        assert diff == pytest.approx(0.0, abs=1e-10)

    @given(a=st.floats(min_value=-360, max_value=360), b=st.floats(min_value=-360, max_value=360))
    @settings(max_examples=80)
    def test_angle_diff_antisymmetry(self, a, b):
        diff_ab = _angle_diff_deg(a, b)
        diff_ba = _angle_diff_deg(b, a)
        assert diff_ab == pytest.approx(-diff_ba, abs=1e-10)


class TestAntennaGainFactorProperties:
    @given(bearing=st.floats(min_value=0, max_value=360))
    @settings(max_examples=50)
    def test_omni_gain_is_zero(self, bearing):
        result = antenna_gain_factor(bearing, None, 360.0)
        assert result == 0.0

    @given(
        bearing=st.floats(min_value=0, max_value=360),
        azimuth=st.floats(min_value=0, max_value=360),
        beamwidth=st.floats(min_value=1.0, max_value=359.0),
        front_back=st.floats(min_value=1.0, max_value=60.0),
    )
    @settings(max_examples=100)
    def test_gain_is_never_positive(self, bearing, azimuth, beamwidth, front_back):
        result = antenna_gain_factor(bearing, azimuth, beamwidth, front_back)
        assert result <= 0.0

    @given(
        bearing=st.floats(min_value=0, max_value=360),
        azimuth=st.floats(min_value=0, max_value=360),
        front_back=st.floats(min_value=1.0, max_value=60.0),
    )
    @settings(max_examples=80)
    def test_direct_sector_gain_at_boresight(self, bearing, azimuth, front_back):
        result = antenna_gain_factor(azimuth, azimuth, 90.0, front_back)
        assert result == pytest.approx(0.0, abs=0.01)


class TestAntennaConfigFromValues:
    @given(
        azimuth=st.floats(min_value=0, max_value=360, allow_nan=False),
        beamwidth_h=st.floats(min_value=1.0, max_value=360.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_omni_returns_omni_config(self, azimuth, beamwidth_h):
        config = antenna_config_from_values("omni", azimuth_deg=azimuth,
                                              horizontal_beamwidth_deg=beamwidth_h)
        assert config.preset == "omni"
        assert config.azimuth_deg is None

    @given(preset_key=st.sampled_from(ANTENNA_PRESET_KEYS))
    @settings(max_examples=len(ANTENNA_PRESET_KEYS))
    def test_preset_key_roundtrip(self, preset_key):
        config = antenna_config_from_values(preset_key)
        assert config.preset == preset_key