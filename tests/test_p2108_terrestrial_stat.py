# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.

import math

import pytest

from clutter.p2108_terrestrial_stat import (
    _L_l,
    _L_s,
    clutter_loss_p2108_terrestrial_stat,
    clutter_loss_p2108_terrestrial_stat_vec,
)


class TestLL:
    def test_at_1_ghz(self):
        val = _L_l(1.0)
        assert val == pytest.approx(
            -2.0 * math.log10(10.0 ** (-5.0 * 0.0 - 12.5) + 10.0 ** (-16.5)), abs=0.01
        )

    def test_approximately_25_db_at_1_ghz(self):
        assert _L_l(1.0) == pytest.approx(25.0, abs=0.5)


class TestLS:
    def test_at_1km_1ghz(self):
        assert _L_s(1.0, 1.0) == pytest.approx(32.98, abs=0.01)

    def test_increases_with_distance(self):
        assert _L_s(10.0, 1.0) > _L_s(1.0, 1.0)

    def test_increases_with_frequency(self):
        assert _L_s(1.0, 10.0) > _L_s(1.0, 1.0)


class TestClutterLossTerrestrialStat:
    def test_p50_combines_deterministic_median(self):
        result = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=50.0)
        L_l = _L_l(1.0)
        L_s = _L_s(1.0, 1.0)
        expected = -5.0 * math.log10(10.0 ** (-0.2 * L_l) + 10.0 ** (-0.2 * L_s))
        assert result == pytest.approx(expected, abs=0.01)

    def test_loss_is_non_negative(self):
        for d in [0.25, 0.5, 1.0, 5.0, 50.0]:
            for f in [0.5, 1.0, 10.0, 67.0]:
                assert clutter_loss_p2108_terrestrial_stat(d, f, p=50.0) >= 0.0

    def test_monotonic_in_percentile(self):
        loss_5 = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=5.0)
        loss_50 = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=50.0)
        loss_95 = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=95.0)
        assert loss_5 < loss_50 < loss_95

    def test_capped_at_2km(self):
        loss_2km = clutter_loss_p2108_terrestrial_stat(2.0, 1.0, p=50.0)
        loss_10km = clutter_loss_p2108_terrestrial_stat(10.0, 1.0, p=50.0)
        assert loss_10km == pytest.approx(loss_2km, abs=0.01)

    def test_capped_at_2km_high_percentile(self):
        loss_2km_p95 = clutter_loss_p2108_terrestrial_stat(2.0, 1.0, p=95.0)
        loss_10km_p95 = clutter_loss_p2108_terrestrial_stat(10.0, 1.0, p=95.0)
        assert loss_10km_p95 == pytest.approx(loss_2km_p95, abs=0.01)
        loss_2km_p5 = clutter_loss_p2108_terrestrial_stat(2.0, 1.0, p=5.0)
        loss_10km_p5 = clutter_loss_p2108_terrestrial_stat(10.0, 1.0, p=5.0)
        assert loss_10km_p5 == pytest.approx(loss_2km_p5, abs=0.01)

    def test_frequency_clamped_low(self):
        result_low = clutter_loss_p2108_terrestrial_stat(1.0, 0.1)
        result_at_min = clutter_loss_p2108_terrestrial_stat(1.0, 0.5)
        assert result_low == pytest.approx(result_at_min, abs=0.01)

    def test_distance_clamped_low(self):
        result_tiny = clutter_loss_p2108_terrestrial_stat(0.01, 1.0)
        result_min = clutter_loss_p2108_terrestrial_stat(0.25, 1.0)
        assert result_tiny == pytest.approx(result_min, abs=0.01)

    def test_pinned_anchor_f1_d1_p50(self):
        L_l = _L_l(1.0)
        L_s = _L_s(1.0, 1.0)
        L_l_expected = -2.0 * math.log10(10.0 ** (-12.5) + 10.0 ** (-16.5))
        assert L_l == pytest.approx(L_l_expected, abs=0.001)
        assert L_s == pytest.approx(32.98, abs=0.001)
        result = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=50.0)
        assert 20.0 < result < 30.0


class TestVectorized:
    def test_vectorized_matches_scalar(self):
        distances = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
        vec = clutter_loss_p2108_terrestrial_stat_vec(distances, 1.0, p=50.0)
        for i, d in enumerate(distances):
            scalar = clutter_loss_p2108_terrestrial_stat(d, 1.0, p=50.0)
            assert vec[i] == pytest.approx(scalar, abs=0.02)

    def test_vectorized_shape(self):
        d = [1.0, 2.0, 3.0]
        result = clutter_loss_p2108_terrestrial_stat_vec(d, 1.0)
        assert len(result) == 3