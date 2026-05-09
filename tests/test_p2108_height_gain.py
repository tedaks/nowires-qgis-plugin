# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

import math

import numpy as np
import pytest

from p2108_height_gain import (
    _J_nu,
    height_gain_loss,
    height_gain_loss_vec,
)


class TestJNu:
    def test_zero_for_nu_below_minus_078(self):
        assert _J_nu(-0.78) == 0.0
        assert _J_nu(-1.0) == 0.0
        assert _J_nu(-10.0) == 0.0

    def test_positive_above_threshold(self):
        assert _J_nu(0.0) > 0.0
        assert _J_nu(1.0) > _J_nu(0.0)

    def test_known_value_nu_0(self):
        expected = 6.9 + 20.0 * math.log10(
            math.sqrt((0.0 - 0.1) ** 2 + 1.0) + 0.0 - 0.1
        )
        assert _J_nu(0.0) == pytest.approx(expected, abs=1e-10)


class TestHeightGainLoss:
    def test_open_category_returns_zero(self):
        assert height_gain_loss(2.0, 1.0, "open") == 0.0

    def test_unknown_category_returns_zero(self):
        assert height_gain_loss(2.0, 1.0, "nonexistent") == 0.0

    def test_antenna_above_R_returns_zero(self):
        assert height_gain_loss(30.0, 1.0, "urban") == 0.0

    def test_urban_method_2a(self):
        h = 2.0
        f = 1.0
        R = 20
        w_s = 27.0
        h_dif = R - h
        theta_clut = math.degrees(math.atan(h_dif / w_s))
        K_nu = 0.342 * math.sqrt(f)
        nu = K_nu * math.sqrt(h_dif * theta_clut)
        J = _J_nu(nu)
        expected = max(0.0, J - 6.03)
        result = height_gain_loss(h, f, "urban", w_s_m=w_s)
        assert result == pytest.approx(expected, abs=0.01)

    def test_open_rural_method_2b(self):
        h = 2.0
        f = 1.0
        R = 10
        Kh2 = 21.8 + 6.2 * math.log10(f)
        expected = max(0.0, -Kh2 * math.log10(h / R))
        result = height_gain_loss(h, f, "open_rural")
        assert result == pytest.approx(expected, abs=0.01)
        assert result == pytest.approx(15.24, abs=0.2)

    def test_suburban_method_2a(self):
        result = height_gain_loss(2.0, 1.0, "suburban")
        assert result > 0.0

    def test_loss_decreases_with_height(self):
        low = height_gain_loss(2.0, 1.0, "urban")
        high = height_gain_loss(15.0, 1.0, "urban")
        assert high < low

    def test_loss_zero_at_R(self):
        assert height_gain_loss(20.0, 1.0, "urban") == 0.0

    def test_frequency_out_of_range_clamped(self):
        result_low = height_gain_loss(2.0, 0.01, "urban")
        result_min = height_gain_loss(2.0, 0.03, "urban")
        assert result_low == pytest.approx(result_min, abs=0.01)


class TestHeightGainLossVec:
    def test_vectorized_matches_scalar(self):
        heights = [2.0, 5.0, 10.0, 15.0, 20.0]
        categories = ["urban", "suburban", "open_rural", "dense_rural", "open"]
        vec = height_gain_loss_vec(heights, 1.0, categories)
        for i, (h, c) in enumerate(zip(heights, categories)):
            scalar = height_gain_loss(h, 1.0, c)
            assert vec[i] == pytest.approx(scalar, abs=0.001)

    def test_vectorized_returns_zeros_for_open(self):
        h = [2.0, 5.0]
        cats = ["open", "open"]
        result = height_gain_loss_vec(h, 1.0, cats)
        np.testing.assert_array_equal(result, [0.0, 0.0])