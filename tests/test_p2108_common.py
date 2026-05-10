# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.

import pytest

from p2108_common import (
    f_inv_normal,
    q_inv_complementary_normal,
    validate_distance_km,
    validate_frequency_ghz,
)


class TestQInvComplementaryNormal:
    def test_at_50_percent(self):
        assert q_inv_complementary_normal(50.0) == pytest.approx(0.0, abs=1e-10)

    def test_positive_at_low_percentile(self):
        assert q_inv_complementary_normal(5.0) > 0.0

    def test_negative_at_high_percentile(self):
        assert q_inv_complementary_normal(95.0) < 0.0

    def test_q_inv_5_greater_than_zero_greater_than_q_inv_95(self):
        assert q_inv_complementary_normal(5.0) > 0.0 > q_inv_complementary_normal(95.0)

    def test_symmetry(self):
        assert q_inv_complementary_normal(5.0) == pytest.approx(-q_inv_complementary_normal(95.0), abs=1e-10)

    def test_known_value(self):
        q5 = q_inv_complementary_normal(5.0)
        f5 = f_inv_normal(5.0)
        assert q5 == pytest.approx(-f5, abs=1e-10)

    def test_approaches_negative_infinity_at_100(self):
        v = q_inv_complementary_normal(99.99)
        assert v < -3.0

    def test_approaches_positive_infinity_at_0(self):
        v = q_inv_complementary_normal(0.01)
        assert v > 3.0


class TestFInvNormal:
    def test_at_50_percent(self):
        assert f_inv_normal(50.0) == pytest.approx(0.0, abs=1e-10)

    def test_negative_at_low_percentile(self):
        assert f_inv_normal(5.0) < 0.0

    def test_positive_at_high_percentile(self):
        assert f_inv_normal(95.0) > 0.0

    def test_f_inv_5_less_than_0_less_than_f_inv_95(self):
        assert f_inv_normal(5.0) < 0.0 < f_inv_normal(95.0)

    def test_symmetry(self):
        assert f_inv_normal(5.0) == pytest.approx(-f_inv_normal(95.0), abs=1e-10)

    def test_known_value_prob25(self):
        assert f_inv_normal(25.0) == pytest.approx(-0.6745, abs=0.001)

    def test_known_value_prob75(self):
        assert f_inv_normal(75.0) == pytest.approx(0.6745, abs=0.001)


class TestSignConventionGuard:
    """Critical: Q^-1 and F^-1 have opposite sign conventions."""

    def test_q_inv_positive_at_p5_f_inv_negative_at_p5(self):
        assert q_inv_complementary_normal(5.0) > 0.0
        assert f_inv_normal(5.0) < 0.0

    def test_q_inv_negative_at_p95_f_inv_positive_at_p95(self):
        assert q_inv_complementary_normal(95.0) < 0.0
        assert f_inv_normal(95.0) > 0.0

    def test_q_inv_equals_negative_f_inv_at_same_p(self):
        for p in [1.0, 5.0, 10.0, 25.0, 50.0, 75.0, 90.0, 95.0, 99.0]:
            assert q_inv_complementary_normal(p) == pytest.approx(
                -f_inv_normal(p), abs=1e-10
            ), f"Mismatch at p={p}"


class TestValidateFrequency:
    def test_in_range(self):
        f, clamped = validate_frequency_ghz(1.0, 0.5, 67.0)
        assert f == 1.0 and not clamped

    def test_below_range(self):
        f, clamped = validate_frequency_ghz(0.1, 0.5, 67.0)
        assert f == 0.5 and clamped

    def test_above_range(self):
        f, clamped = validate_frequency_ghz(100.0, 0.5, 67.0)
        assert f == 67.0 and clamped


class TestValidateDistance:
    def test_in_range(self):
        d, clamped = validate_distance_km(5.0, min_km=0.25)
        assert d == 5.0 and not clamped

    def test_below_minimum(self):
        d, clamped = validate_distance_km(0.1, min_km=0.25)
        assert d == 0.25 and clamped

    def test_no_min(self):
        d, clamped = validate_distance_km(0.01)
        assert d == 0.01 and not clamped