# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Unit tests for fresnel.py — Fresnel zone, earth bulge, and profile analysis."""

import math

import numpy as np
import pytest

from fresnel import fresnel_radius, earth_bulge, fresnel_profile_analysis
from constants import EARTH_RADIUS_M, FRESNEL_60PCT_FACTOR

C_LIGHT = 299792458.0


class TestFresnelRadius:
    """Tests for fresnel_radius()."""

    def test_zero_d1_returns_zero(self):
        assert fresnel_radius(0, 100, 300) == 0.0

    def test_zero_d2_returns_zero(self):
        assert fresnel_radius(100, 0, 300) == 0.0

    def test_negative_d1_returns_zero(self):
        assert fresnel_radius(-10, 100, 300) == 0.0

    def test_negative_d2_returns_zero(self):
        assert fresnel_radius(100, -10, 300) == 0.0

    def test_both_zero_returns_zero(self):
        assert fresnel_radius(0, 0, 300) == 0.0

    def test_both_negative_returns_zero(self):
        assert fresnel_radius(-10, -20, 300) == 0.0

    def test_midpoint_matches_formula(self):
        f_mhz = 300.0
        wavelength = C_LIGHT / (f_mhz * 1e6)
        d1 = d2 = 500.0
        expected = math.sqrt(wavelength * d1 * d2 / (d1 + d2))
        result = fresnel_radius(d1, d2, f_mhz)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_asymmetric_distances(self):
        f_mhz = 300.0
        wavelength = C_LIGHT / (f_mhz * 1e6)
        d1 = 200.0
        d2 = 800.0
        expected = math.sqrt(wavelength * d1 * d2 / (d1 + d2))
        assert fresnel_radius(d1, d2, f_mhz) == pytest.approx(expected, rel=1e-10)

    def test_lower_frequency_larger_radius(self):
        r_low = fresnel_radius(500, 500, 100)
        r_high = fresnel_radius(500, 500, 1000)
        assert r_low > r_high

    def test_frequency_scaling(self):
        r_100 = fresnel_radius(500, 500, 100)
        r_400 = fresnel_radius(500, 500, 400)
        assert r_100 == pytest.approx(r_400 * 2.0, rel=0.01)

    def test_very_high_frequency(self):
        r = fresnel_radius(100, 100, 100000)
        assert r > 0.0
        wavelength = C_LIGHT / (100000 * 1e6)
        expected = math.sqrt(wavelength * 100 * 100 / 200)
        assert r == pytest.approx(expected, rel=1e-10)

    def test_very_large_distances(self):
        d1 = d2 = 1e6
        r = fresnel_radius(d1, d2, 300)
        assert r > 0.0
        wavelength = C_LIGHT / (300e6)
        expected = math.sqrt(wavelength * d1 * d2 / (d1 + d2))
        assert r == pytest.approx(expected, rel=1e-10)

    def test_result_positive_for_valid_inputs(self):
        assert fresnel_radius(50, 50, 900) > 0.0

    def test_symmetry(self):
        assert fresnel_radius(200, 800, 300) == pytest.approx(
            fresnel_radius(800, 200, 300), rel=1e-10
        )


class TestEarthBulge:
    """Tests for earth_bulge()."""

    def test_zero_distance(self):
        assert earth_bulge(0, 10000) == 0.0

    def test_end_distance(self):
        assert earth_bulge(10000, 10000) == 0.0

    def test_midpoint_formula(self):
        d_total = 10000.0
        k = 4.0 / 3.0
        d = d_total / 2.0
        a_eff = k * EARTH_RADIUS_M
        expected = d * (d_total - d) / (2.0 * a_eff)
        result = earth_bulge(d, d_total, k_factor=k)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_midpoint_max_bulge(self):
        d_total = 10000.0
        mid = earth_bulge(d_total / 2, d_total)
        off_center = earth_bulge(d_total / 4, d_total)
        assert mid > off_center

    def test_k_factor_geometric(self):
        d_total = 10000.0
        d = 5000.0
        k = 1.0
        a_eff = k * EARTH_RADIUS_M
        expected = d * (d_total - d) / (2.0 * a_eff)
        result = earth_bulge(d, d_total, k_factor=k)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_geometric_larger_than_standard(self):
        d = 5000.0
        d_total = 10000.0
        b_std = earth_bulge(d, d_total, k_factor=4.0 / 3.0)
        b_geo = earth_bulge(d, d_total, k_factor=1.0)
        assert b_geo > b_std

    def test_k_factor_very_large_nearly_flat(self):
        d = 5000.0
        d_total = 10000.0
        b_flat = earth_bulge(d, d_total, k_factor=1e6)
        b_std = earth_bulge(d, d_total, k_factor=4.0 / 3.0)
        assert b_flat < b_std
        assert b_flat == pytest.approx(0.0, abs=1e-3)

    def test_d_exceeds_total_negative_bulge(self):
        d_total = 10000.0
        k = 4.0 / 3.0
        a_eff = k * EARTH_RADIUS_M
        d = 15000.0
        result = earth_bulge(d, d_total, k_factor=k)
        expected = d * (d_total - d) / (2.0 * a_eff)
        assert result < 0
        assert result == pytest.approx(expected, rel=1e-10)

    def test_total_dist_zero_d_zero(self):
        result = earth_bulge(0, 0)
        assert result == 0.0

    def test_total_dist_zero_d_positive(self):
        result = earth_bulge(100, 0)
        assert result < 0

    def test_symmetry_about_midpoint(self):
        d_total = 10000.0
        b_left = earth_bulge(2000, d_total)
        b_right = earth_bulge(8000, d_total)
        assert b_left == pytest.approx(b_right, rel=1e-10)

    def test_default_k_factor(self):
        d = 5000.0
        d_total = 10000.0
        default_result = earth_bulge(d, d_total)
        explicit_result = earth_bulge(d, d_total, k_factor=4.0 / 3.0)
        assert default_result == pytest.approx(explicit_result, rel=1e-10)


class TestFresnelProfileAnalysis:
    """Tests for fresnel_profile_analysis()."""

    def test_clear_path_no_obstruction(self):
        n = 50
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        tx_h = 100.0
        rx_h = 100.0
        wavelength = 1.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, wavelength
            )
        )
        assert not obstructs.any()

    def test_clear_path_no_f1_violation(self):
        n = 50
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 100.0, 100.0, 1000, 1.0
            )
        )
        assert not vf1.any()

    def test_clear_path_no_f60_violation(self):
        n = 50
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 100.0, 100.0, 1000, 1.0
            )
        )
        assert not vf60.any()

    def test_obstructed_path(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        mid = n // 2
        elevations[mid] = 200.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 50.0, 50.0, 1000, 1.0
            )
        )
        assert obstructs.any()

    def test_fresnel_violation_without_los_obstruction(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        mid = n // 2
        tx_h = 100.0
        rx_h = 100.0
        wavelength = 1.0
        fr_midpoint = fresnel_radius(500, 500, 300)
        elevations[mid] = tx_h - fr_midpoint * 0.5
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, wavelength
            )
        )
        assert not obstructs.any()
        assert vf1.any()

    def test_f60_subset_of_f1(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        mid = n // 2
        tx_h = 100.0
        rx_h = 100.0
        wavelength = 1.0
        fr_midpoint = fresnel_radius(500, 500, 300)
        elevations[mid] = tx_h - fr_midpoint * 0.3
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, wavelength
            )
        )
        f60_indices = set(np.where(vf60)[0])
        f1_indices = set(np.where(vf1)[0])
        assert f60_indices.issubset(f1_indices)

    def test_dist_m_zero_raises_value_error(self):
        """dist_m <= 0 is physically meaningless; raise ValueError."""
        n = 20
        distances = np.linspace(0, 100, n)
        elevations = np.full(n, 50.0)
        with pytest.raises(ValueError, match="dist_m > 0"):
            fresnel_profile_analysis(
                distances, elevations, 80.0, 80.0, 0, 1.0
            )

    def test_dist_m_negative_raises_value_error(self):
        """Negative dist_m is physically meaningless; raise ValueError."""
        n = 20
        distances = np.linspace(0, 100, n)
        elevations = np.full(n, 10.0)
        with pytest.raises(ValueError, match="dist_m > 0"):
            fresnel_profile_analysis(
                distances, elevations, 50.0, 50.0, -10, 1.0
            )

    def test_two_point_profile(self):
        distances = np.array([0.0, 1000.0])
        elevations = np.array([0.0, 0.0])
        tx_h = 50.0
        rx_h = 50.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, 1.0
            )
        )
        assert len(terrain_bulge) == 2
        assert len(los_h) == 2
        assert len(fr) == 2
        assert len(obstructs) == 2
        assert len(vf1) == 2
        assert len(vf60) == 2

    def test_two_point_profile_endpoints_fresnel_zero(self):
        distances = np.array([0.0, 1000.0])
        elevations = np.array([0.0, 0.0])
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 50.0, 50.0, 1000, 1.0
            )
        )
        assert fr[0] == 0.0
        assert fr[1] == 0.0

    def test_k_factor_affects_bulge(self):
        n = 50
        distances = np.linspace(0, 1000, n)
        elevations = np.full(n, 50.0)
        tx_h = 80.0
        rx_h = 80.0
        _, los_std, _, _, _, _ = fresnel_profile_analysis(
            distances, elevations, tx_h, rx_h, 1000, 1.0, k_factor=4.0 / 3.0
        )
        _, los_flat, _, _, _, _ = fresnel_profile_analysis(
            distances, elevations, tx_h, rx_h, 1000, 1.0, k_factor=100.0
        )
        np.testing.assert_array_almost_equal(los_std, los_flat)

    def test_k_factor_affects_obstruction(self):
        n = 101
        distances = np.linspace(0, 5000, n)
        elevations = np.full(n, 50.0)
        elevations[n // 2] = 60.0
        tx_h = 70.0
        rx_h = 70.0
        _, _, _, obs_std, _, _ = fresnel_profile_analysis(
            distances, elevations, tx_h, rx_h, 5000, 1.0, k_factor=4.0 / 3.0
        )
        _, _, _, obs_geo, _, _ = fresnel_profile_analysis(
            distances, elevations, tx_h, rx_h, 5000, 1.0, k_factor=1.0
        )
        num_obs_std = obs_std.sum()
        num_obs_geo = obs_geo.sum()
        assert num_obs_geo >= num_obs_std

    def test_fresnel_60pct_factor_applied_correctly(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        tx_h = 100.0
        rx_h = 100.0
        wavelength = 1.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, wavelength
            )
        )
        for i in range(n):
            if vf60[i]:
                threshold = los_h[i] - FRESNEL_60PCT_FACTOR * fr[i]
                assert terrain_bulge[i] > threshold

    def test_f60_implies_terrain_above_60pct_threshold(self):
        n = 101
        distances = np.linspace(0, 2000, n)
        elevations = np.random.uniform(0, 40, n)
        mid = n // 2
        elevations[mid] = 80.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 60.0, 60.0, 2000, 1.0
            )
        )
        f60_idx = np.where(vf60)[0]
        for i in f60_idx:
            assert terrain_bulge[i] > (los_h[i] - FRESNEL_60PCT_FACTOR * fr[i])

    def test_output_dtypes(self):
        n = 20
        distances = np.linspace(0, 500, n)
        elevations = np.ones(n) * 10.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 50.0, 50.0, 500, 1.0
            )
        )
        assert terrain_bulge.dtype == np.float64
        assert los_h.dtype == np.float64
        assert fr.dtype == np.float64
        assert obstructs.dtype == bool
        assert vf1.dtype == bool
        assert vf60.dtype == bool

    def test_los_line_interpolation(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        tx_h = 30.0
        rx_h = 70.0
        wavelength = 1.0
        _, los_h, _, _, _, _ = fresnel_profile_analysis(
            distances, elevations, tx_h, rx_h, 1000, wavelength
        )
        expected_los = tx_h + (distances / 1000.0) * (rx_h - tx_h)
        np.testing.assert_allclose(los_h, expected_los, atol=1e-10)

    def test_fresnel_radius_at_midpoint_profile(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        wavelength = 1.0
        _, _, fr, _, _, _ = fresnel_profile_analysis(
            distances, elevations, 100.0, 100.0, 1000, wavelength
        )
        mid = n // 2
        d_mid = distances[mid]
        d2_mid = 1000 - d_mid
        expected_fr = math.sqrt(wavelength * d_mid * d2_mid / (d_mid + d2_mid))
        assert fr[mid] == pytest.approx(expected_fr, rel=1e-6)

    def test_earth_bulge_at_midpoint_in_profile(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.full(n, 10.0)
        k = 4.0 / 3.0
        a_eff = k * EARTH_RADIUS_M
        terrain_bulge, _, _, _, _, _ = fresnel_profile_analysis(
            distances, elevations, 50.0, 50.0, 1000, 1.0, k_factor=k
        )
        mid = n // 2
        d_mid = distances[mid]
        expected_bulge = 10.0 + d_mid * (1000 - d_mid) / (2.0 * a_eff)
        assert terrain_bulge[mid] == pytest.approx(expected_bulge, rel=1e-6)

    def test_endpoint_fresnel_radius_is_zero(self):
        n = 51
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        _, _, fr, _, _, _ = fresnel_profile_analysis(
            distances, elevations, 50.0, 50.0, 1000, 1.0
        )
        assert fr[0] == 0.0
        assert fr[-1] == 0.0

    def test_terrain_exactly_at_los_still_obstructs(self):
        n = 101
        distances = np.linspace(0, 1000, n)
        elevations = np.full(n, 50.0)
        tx_h = 50.0
        rx_h = 50.0
        terrain_bulge, los_h, fr, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, 1.0
            )
        )
        assert obstructs.sum() > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])