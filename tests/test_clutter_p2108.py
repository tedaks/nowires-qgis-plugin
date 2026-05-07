# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

import math

import numpy as np
import pytest

from clutter_p2108 import clutter_loss_p2108, clutter_loss_p2108_vec


def test_zero_distance_returns_zero():
    assert clutter_loss_p2108(0.0, "urban", 1000.0) == 0.0


def test_open_category_returns_zero():
    assert clutter_loss_p2108(1000.0, "open", 1000.0) == 0.0


def test_unknown_category_returns_zero():
    assert clutter_loss_p2108(1000.0, "nonexistent", 1000.0) == 0.0


def test_urban_at_reference_distance_in_band():
    v = clutter_loss_p2108(500.0, "urban", 3000.0)
    assert 5.0 < v < 12.0


def test_loss_increases_with_distance():
    short = clutter_loss_p2108(100.0, "urban", 3000.0)
    long_ = clutter_loss_p2108(10000.0, "urban", 3000.0)
    assert long_ > short


def test_loss_saturates_at_long_distance():
    a = clutter_loss_p2108(10000.0, "urban", 3000.0)
    b = clutter_loss_p2108(100000.0, "urban", 3000.0)
    assert abs(a - b) < 1.0


def test_frequency_factor_monotone():
    vhf = clutter_loss_p2108(1000.0, "urban", 150.0)
    uhf = clutter_loss_p2108(1000.0, "urban", 3000.0)
    assert uhf > vhf


def test_category_ordering_at_fixed_inputs():
    f, d = 1000.0, 1000.0
    vals = {c: clutter_loss_p2108(d, c, f) for c in
            ["open", "open_rural", "dense_rural", "suburban", "urban"]}
    assert vals["urban"] > vals["suburban"] > vals["dense_rural"] > vals["open_rural"] > vals["open"]


def test_loss_capped_below_base_loss():
    v = clutter_loss_p2108(1_000_000.0, "urban", 5000.0)
    assert v <= 10.0


@pytest.mark.parametrize("category,d,f,expected", [
    ("urban", 200.0, 3000.0, 10.0 * (1 - math.exp(-1.0)) * min(1.0, math.log10(3000.0 / 2000.0) + 0.5)),
    ("suburban", 500.0, 1000.0, 8.0 * (1 - math.exp(-1.0)) * 0.5 * math.log10(10.0)),
])
def test_pinned_numeric_anchors(category, d, f, expected):
    assert clutter_loss_p2108(d, category, f) == pytest.approx(expected, abs=1e-9)


def test_vectorized_matches_scalar():
    distances = np.array([0.0, 100.0, 500.0, 1000.0, 5000.0, 100000.0])
    vec = clutter_loss_p2108_vec(distances, "urban", 1800.0)
    scalar = np.array([clutter_loss_p2108(float(d), "urban", 1800.0) for d in distances])
    assert vec.shape == distances.shape
    np.testing.assert_allclose(vec, scalar, atol=1e-12)


def test_vectorized_unknown_category_returns_zeros():
    out = clutter_loss_p2108_vec(np.array([100.0, 200.0]), "nonsense", 1000.0)
    np.testing.assert_array_equal(out, np.zeros(2))