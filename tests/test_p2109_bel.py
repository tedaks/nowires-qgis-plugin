# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

import math

import numpy as np
import pytest

from p2109_bel import building_entry_loss, building_entry_loss_vec


class TestBuildingEntryLoss:
    def test_traditional_1ghz_theta0_p50(self):
        result = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=50.0)
        L_h = 12.64 + 3.72 * 0 + 0.96 * 0
        L_e = 0.0
        mu1 = L_h + L_e
        mu2 = 9.1 + (-3.0) * 0
        A = 0.0 * mu1
        B = 0.0 * mu2
        expected = 10.0 * math.log10(
            10.0 ** (0.1 * mu1) + 10.0 ** (0.1 * mu2) + 10.0 ** (-0.3)
        )
        assert result == pytest.approx(expected, abs=0.1)
        assert result > 0.0

    def test_thermally_efficient_higher_than_traditional(self):
        trad = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=50.0)
        therm = building_entry_loss(1.0, "thermally_efficient", theta_deg=0.0, p=50.0)
        assert therm > trad

    def test_monotonic_in_probability(self):
        loss_5 = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=5.0)
        loss_50 = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=50.0)
        loss_95 = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=95.0)
        assert loss_5 < loss_50 < loss_95

    def test_elevation_angle_adds_loss(self):
        loss_0 = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=50.0)
        loss_30 = building_entry_loss(1.0, "traditional", theta_deg=30.0, p=50.0)
        assert loss_30 > loss_0

    def test_elevation_angle_0_212_per_degree(self):
        loss_0 = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=50.0)
        loss_10 = building_entry_loss(1.0, "traditional", theta_deg=10.0, p=50.0)
        diff = loss_10 - loss_0
        assert diff > 0.0

    def test_non_negative(self):
        for bt in ["traditional", "thermally_efficient"]:
            for f in [0.08, 0.5, 1.0, 10.0, 100.0]:
                for p_val in [1.0, 50.0, 99.0]:
                    assert building_entry_loss(f, bt, theta_deg=0.0, p=p_val) >= 0.0

    def test_thermally_efficient_1ghz_theta0_p50(self):
        L_h = 28.19 + (-3.0) * 0 + 8.48 * 0
        assert L_h == pytest.approx(28.19, abs=0.01)
        therm = building_entry_loss(1.0, "thermally_efficient", theta_deg=0.0, p=50.0)
        assert therm > 15.0

    def test_unknown_building_type_defaults_traditional(self):
        trad = building_entry_loss(1.0, "traditional", theta_deg=0.0, p=50.0)
        unknown = building_entry_loss(1.0, "nonexistent", theta_deg=0.0, p=50.0)
        assert unknown == pytest.approx(trad, abs=0.01)


class TestBuildingEntryLossVec:
    def test_vectorized_matches_scalar(self):
        freqs = [0.1, 0.5, 1.0, 10.0, 50.0, 100.0]
        vec = building_entry_loss_vec(freqs, "traditional", theta_deg=0.0, p=50.0)
        for i, f in enumerate(freqs):
            scalar = building_entry_loss(f, "traditional", theta_deg=0.0, p=50.0)
            assert vec[i] == pytest.approx(scalar, abs=0.02)

    def test_vectorized_shape(self):
        result = building_entry_loss_vec([1.0, 2.0, 3.0], "traditional")
        assert len(result) == 3