# -*- coding: utf-8 -*-
"""Unit tests for radio.py — Fresnel zone analysis and signal levels."""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from radio import (
    fresnel_radius,
    earth_bulge,
    fresnel_profile_analysis,
    SIGNAL_LEVELS,
    THRESHOLDS,
    build_pfl,
    interpolate_nans,
)


class TestFresnelRadius:
    """Tests for fresnel_radius()."""

    def test_zero_distance_returns_zero(self):
        """Fresnel radius should be 0 when either d1 or d2 is 0."""
        assert fresnel_radius(0, 100, 300) == 0.0
        assert fresnel_radius(100, 0, 300) == 0.0

    def test_midpoint_fresnel_radius(self):
        """At the midpoint (d1 == d2), Fresnel radius should equal
        sqrt(wavelength * d / 4) for d1 = d2 = d/2."""
        f_mhz = 300.0  # 1m wavelength
        d = 1000.0  # 1km total distance
        r_mid = fresnel_radius(500, 500, f_mhz)
        wavelength = 299792458.0 / (f_mhz * 1e6)
        expected = math.sqrt(wavelength * 500 * 500 / 1000)
        assert r_mid == pytest.approx(expected, rel=0.01)

    def test_fresnel_radius_decreases_with_frequency(self):
        """Higher frequency = smaller Fresnel radius."""
        r_low = fresnel_radius(500, 500, 100)
        r_high = fresnel_radius(500, 500, 1000)
        assert r_low > r_high


class TestEarthBulge:
    """Tests for earth_bulge()."""

    def test_zero_distance(self):
        """Earth bulge at d=0 should be 0."""
        assert earth_bulge(0, 1000, k_factor=4.0/3.0) == 0.0

    def test_midpoint_bulge(self):
        """At midpoint, bulge = d_total / (8 * a_eff) * d_total."""
        k = 4.0 / 3.0
        a_eff = k * 6371000.0
        d_total = 10000.0
        # At midpoint d = d_total/2
        d = d_total / 2.0
        expected = d * (d_total - d) / (2.0 * a_eff)
        result = earth_bulge(d, d_total, k_factor=k)
        assert result == pytest.approx(expected, rel=1e-6)


class TestFresnelProfileAnalysis:
    """Tests for fresnel_profile_analysis()."""

    def test_clear_path(self):
        """When terrain is well below LOS, nothing should be obstructed."""
        # Flat terrain at 0m, antennas at 100m and 100m, 1km path, 300 MHz
        n = 50
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)  # flat ground
        tx_h = 100.0 + 0.0  # antenna height + ground
        rx_h = 100.0 + 0.0
        wavelength = 1.0  # 300 MHz

        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, wavelength
            )
        )
        # Flat terrain should not obstruct LOS
        assert not obstructs.any()

    def test_obstructed_path(self):
        """A terrain peak above LOS should be flagged as obstructed."""
        n = 50
        distances = np.linspace(0, 1000, n)
        elevations = np.zeros(n)
        elevations[25] = 200.0  # mountain in the middle
        tx_h = 50.0
        rx_h = 50.0
        wavelength = 1.0

        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, tx_h, rx_h, 1000, wavelength
            )
        )
        assert obstructs.any()

    def test_output_shapes(self):
        """All output arrays should have the same length as input."""
        n = 30
        distances = np.linspace(0, 500, n)
        elevations = np.random.rand(n) * 50
        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                distances, elevations, 100, 100, 500, 1.0
            )
        )
        assert len(terrain_bulge) == n
        assert len(los_h) == n
        assert len(fresnel_r) == n
        assert len(obstructs) == n
        assert len(vf1) == n
        assert len(vf60) == n


class TestBuildPFL:
    """Tests for build_pfl()."""

    def test_basic_pfl(self):
        """PFL format should start with n-1 and step."""
        elevs = [100, 110, 105, 120]
        step = 30.0
        pfl = build_pfl(elevs, step)
        assert pfl[0] == 3  # n-1 = len(elevs)-1
        assert pfl[1] == 30.0
        assert len(pfl) == 2 + len(elevs)

    def test_numpy_array_input(self):
        """Should work with numpy arrays too."""
        elevs = np.array([100, 110, 105])
        pfl = build_pfl(elevs, 50.0)
        assert pfl[0] == 2
        assert pfl[1] == 50.0


class TestInterpolateNans:
    """Tests for interpolate_nans()."""

    def test_no_nans(self):
        """Array with no NaNs should be returned unchanged."""
        values = [1.0, 2.0, 3.0, 4.0]
        result = interpolate_nans(values)
        assert result == [1.0, 2.0, 3.0, 4.0]

    def test_all_nans(self):
        """All-NaN array should be returned as-is (can't interpolate)."""
        values = [float("nan"), float("nan"), float("nan")]
        result = interpolate_nans(values)
        assert all(math.isnan(v) for v in result)

    def test_interpolate_middle_nan(self):
        """NaN in the middle should be interpolated from neighbors."""
        values = [1.0, float("nan"), 3.0]
        result = interpolate_nans(values)
        assert result[1] == pytest.approx(2.0, abs=0.01)

    def test_interpolate_multiple_nans(self):
        """Multiple NaNs should be linearly interpolated."""
        values = [0.0, float("nan"), float("nan"), 3.0]
        result = interpolate_nans(values)
        assert result[1] == pytest.approx(1.0, abs=0.01)
        assert result[2] == pytest.approx(2.0, abs=0.01)


class TestSignalLevels:
    """Tests for signal level definitions."""

    def test_thresholds_ordering(self):
        """Thresholds should be in descending order."""
        for i in range(len(THRESHOLDS) - 1):
            assert THRESHOLDS[i] > THRESHOLDS[i + 1]

    def test_signal_levels_count(self):
        """Should have 6 signal levels."""
        assert len(SIGNAL_LEVELS) == 6

    def test_signal_levels_structure(self):
        """Each entry should be (threshold, (r, g, b, a), label)."""
        for threshold, rgba, label in SIGNAL_LEVELS:
            assert isinstance(threshold, float)
            assert len(rgba) == 4
            assert isinstance(label, str)


import pytest

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
