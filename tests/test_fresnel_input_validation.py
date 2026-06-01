# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for missing f_mhz and k_factor validation in Fresnel.

Before the fix, fresnel_radius did not validate f_mhz (zero/negative caused
ZeroDivisionError or ValueError), and fresnel_profile_analysis / earth_bulge
did not validate k_factor (zero caused silent inf/nan arrays).
"""
import numpy as np

from fresnel import fresnel_radius, fresnel_profile_analysis, earth_bulge


class TestFresnelRadiusFmhzGuard:
    def test_zero_fmhz_returns_zero(self):
        assert fresnel_radius(100, 100, 0) == 0.0

    def test_negative_fmhz_returns_zero(self):
        assert fresnel_radius(100, 100, -100) == 0.0

    def test_valid_fmhz_returns_positive(self):
        result = fresnel_radius(100, 100, 300)
        assert result > 0


class TestEarthBulgeKfactorGuard:
    def test_zero_kfactor_returns_zero(self):
        assert earth_bulge(100, 1000, k_factor=0) == 0.0

    def test_negative_kfactor_returns_zero(self):
        assert earth_bulge(100, 1000, k_factor=-1) == 0.0

    def test_valid_kfactor_returns_positive(self):
        result = earth_bulge(100, 1000, k_factor=4.0 / 3.0)
        assert result > 0


class TestFresnelProfileKfactorGuard:
    def test_zero_kfactor_returns_finite_arrays(self):
        distances = np.array([0, 100, 200], dtype=float)
        elevations = np.array([10, 20, 10], dtype=float)
        terrain_bulge, los_h, fresnel_r, obs, vf1, vf60 = fresnel_profile_analysis(
            distances, elevations, 50.0, 40.0, 200.0, 0.3, k_factor=0)
        assert np.all(np.isfinite(terrain_bulge))
        assert np.all(np.isfinite(los_h))

    def test_negative_kfactor_returns_finite_arrays(self):
        distances = np.array([0, 100, 200], dtype=float)
        elevations = np.array([10, 20, 10], dtype=float)
        terrain_bulge, los_h, fresnel_r, obs, vf1, vf60 = fresnel_profile_analysis(
            distances, elevations, 50.0, 40.0, 200.0, 0.3, k_factor=-1)
        assert np.all(np.isfinite(terrain_bulge))
        assert np.all(np.isfinite(los_h))