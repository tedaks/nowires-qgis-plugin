# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Property-based tests for radio.py using hypothesis."""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from radio import (
    K_FACTOR_PRESETS,
    ITM_MIN_TERMINAL_HEIGHT_M,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MAX_N0,
    ITM_MIN_SIGMA,
    resolve_k_factor,
    validate_itm_input_ranges,
    build_pfl,
)


class TestResolveKFactorProperties:
    @given(
        has_preset=st.booleans(),
        has_custom=st.booleans(),
        custom_value=st.floats(min_value=0.1, max_value=10.0),
        preset_index=st.integers(min_value=0, max_value=len(K_FACTOR_PRESETS) - 1),
    )
    @settings(max_examples=50)
    def test_resolve_k_factor_returns_positive_float(
        self, has_preset, has_custom, custom_value, preset_index
    ):
        result = resolve_k_factor(has_preset, has_custom, custom_value, preset_index)
        assert isinstance(result, float)
        assert result > 0

    @given(preset_index=st.integers(min_value=0, max_value=len(K_FACTOR_PRESETS) - 1))
    @settings(max_examples=20)
    def test_resolve_k_factor_preset_returns_known_value(self, preset_index):
        result = resolve_k_factor(True, False, 0.0, preset_index)
        assert result == K_FACTOR_PRESETS[preset_index]

    @given(custom_value=st.floats(min_value=0.1, max_value=10.0))
    @settings(max_examples=30)
    def test_resolve_k_factor_custom_returns_custom(self, custom_value):
        result = resolve_k_factor(False, True, custom_value, 0)
        assert result == custom_value


class TestValidateITMRangesProperties:
    @given(
        tx_h=st.floats(min_value=ITM_MIN_TERMINAL_HEIGHT_M, max_value=ITM_MAX_TERMINAL_HEIGHT_M),
        rx_h=st.floats(min_value=ITM_MIN_TERMINAL_HEIGHT_M, max_value=ITM_MAX_TERMINAL_HEIGHT_M),
        freq=st.floats(min_value=ITM_MIN_FREQUENCY_MHZ, max_value=ITM_MAX_FREQUENCY_MHZ),
        n0=st.floats(min_value=ITM_MIN_N0, max_value=ITM_MAX_N0),
        sigma=st.floats(min_value=ITM_MIN_SIGMA, max_value=100.0),
    )
    @settings(max_examples=50)
    def test_valid_ranges_do_not_raise(self, tx_h, rx_h, freq, n0, sigma):
        validate_itm_input_ranges(tx_h, rx_h, freq, n0, sigma)

    @given(
        tx_h=st.floats(max_value=ITM_MIN_TERMINAL_HEIGHT_M - 0.01,
                       allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_tx_height_below_min_raises(self, tx_h):
        assume(tx_h != 0)
        with pytest.raises(ValueError, match="TX antenna height"):
            validate_itm_input_ranges(tx_h, 10.0, 300.0, 301.0, 0.005)

    @given(freq=st.floats(max_value=ITM_MIN_FREQUENCY_MHZ - 0.01,
                          allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_freq_below_min_raises(self, freq):
        assume(freq != 0)
        with pytest.raises(ValueError, match="Frequency"):
            validate_itm_input_ranges(30.0, 10.0, freq, 301.0, 0.005)


class TestBuildPflProperties:
    @given(
        elevations=st.lists(
            st.floats(min_value=-500, max_value=9000, allow_nan=False,
                      allow_infinity=False),
            min_size=2, max_size=500,
        ),
        step_m=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_pfl_first_two_elements_are_count_and_step(self, elevations, step_m):
        assume(step_m > 0)
        pfl = build_pfl(elevations, step_m)
        n = max(len(elevations) - 1, 1)
        assert pfl[0] == float(n)
        assert pfl[1] == float(step_m)
        assert len(pfl) == 2 + len(elevations)

    @given(step_m=st.floats(min_value=1.0, max_value=500.0))
    @settings(max_examples=10)
    def test_pfl_single_elevation(self, step_m):
        pfl = build_pfl([100.0], step_m)
        assert pfl[0] == 1.0
        assert len(pfl) == 3