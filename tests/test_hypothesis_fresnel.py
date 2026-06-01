# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Property-based tests for fresnel.py using hypothesis."""

import math
import numpy as np
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from fresnel import fresnel_radius, earth_bulge, fresnel_profile_analysis


class TestFresnelRadiusProperties:
    @given(
        d1=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False),
        d2=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False),
        freq=st.floats(min_value=20.0, max_value=20000.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_fresnel_radius_is_positive_and_finite(self, d1, d2, freq):
        result = fresnel_radius(d1, d2, freq)
        assert result > 0
        assert math.isfinite(result)

    @given(freq=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False))
    @settings(max_examples=30)
    def test_fresnel_radius_decreases_with_frequency(self, freq):
        r_low = fresnel_radius(500.0, 500.0, freq)
        r_high = fresnel_radius(500.0, 500.0, freq * 2)
        assert r_high < r_low

    @given(d=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False))
    @settings(max_examples=30)
    def test_symmetry_of_fresnel_radius(self, d):
        r1 = fresnel_radius(d, 500.0, 300.0)
        r2 = fresnel_radius(500.0, d, 300.0)
        assert r1 == pytest.approx(r2, rel=1e-10)


class TestEarthBulgeProperties:
    @given(
        d=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False),
        total=st.floats(min_value=1.0, max_value=200000.0, allow_nan=False),
        k=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
    )
    @settings(max_examples=80)
    def test_earth_bulge_non_negative(self, d, total, k):
        assume(d <= total)
        result = earth_bulge(d, total, k_factor=k)
        assert result >= 0.0

    @given(k=st.floats(min_value=1.0, max_value=4.0, allow_nan=False))
    @settings(max_examples=30)
    def test_bulge_decreases_with_larger_k(self, k):
        total = 10000.0
        d = 5000.0
        b_small_k = earth_bulge(d, total, k_factor=0.67)
        b_large_k = earth_bulge(d, total, k_factor=k)
        if k > 0.67:
            assert b_large_k < b_small_k


class TestFresnelProfileAnalysisProperties:
    @given(
        dist_m=st.floats(min_value=100.0, max_value=50000.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_profile_analysis_returns_correct_shapes(self, dist_m):
        n = 20
        distances = np.linspace(0, dist_m, n)
        elevations = np.full(n, 100.0)
        tx_h = 130.0
        rx_h = 110.0
        wavelength_m = 1.0
        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(distances, elevations, tx_h, rx_h, dist_m, wavelength_m)
        )
        assert terrain_bulge.shape == (n,)
        assert los_h.shape == (n,)
        assert fresnel_r.shape == (n,)
        assert obstructs.shape == (n,)
        assert vf1.shape == (n,)
        assert vf60.shape == (n,)

    @given(
        dist_m=st.floats(min_value=100.0, max_value=50000.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_flat_terrain_no_los_obstruction(self, dist_m):
        n = 20
        distances = np.linspace(0, dist_m, n)
        elevations = np.full(n, 100.0)
        tx_h = 130.0
        rx_h = 110.0
        wavelength_m = 1.0
        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(distances, elevations, tx_h, rx_h, dist_m, wavelength_m)
        )
        assert not obstructs.all()