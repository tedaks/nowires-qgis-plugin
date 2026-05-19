# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
import pytest
from clutter.constants import MAX_CLUTTER_LOSS
from clutter.saalos import clutter_loss_saalos


@pytest.mark.parametrize("d,cch,h_tx,h_rx,h_gnd,pol,f", [
    (1000.0, 0.0, 10.0, 2.0, 0.0, 0, 1000.0),
    (0.0, 15.0, 10.0, 2.0, 0.0, 0, 1000.0),
    (1000.0, 10.0, 30.0, 15.0, 0.0, 0, 1000.0),
    (1000.0, 15.0, 30.0, 15.0, 0.0, 0, 1000.0),
])
def test_boundary_returns_zero(d, cch, h_tx, h_rx, h_gnd, pol, f):
    if h_rx >= cch:
        assert clutter_loss_saalos(d, cch, h_tx, h_rx, h_gnd, pol, f) == 0.0
    else:
        assert clutter_loss_saalos(d, cch, h_tx, h_rx, h_gnd, pol, f) == 0.0


@pytest.mark.parametrize("d,expected", [
    (100.0, 4.888360),
    (150.0, 7.079108),
    (200.0, 9.301259),
])
def test_distance_reference_values_h_pol(d, expected):
    actual = clutter_loss_saalos(d, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    assert actual == pytest.approx(expected, abs=1e-3)


@pytest.mark.parametrize("h_rx,expected", [
    (0.0, 13.497084),
    (2.0, 9.301259),
    (5.0, 5.983496),
    (10.0, 3.110594),
    (14.9, 0.025907),
])
def test_rx_height_reference_values(h_rx, expected):
    actual = clutter_loss_saalos(200.0, 15.0, 30.0, h_rx, 0.0, 0, 1000.0)
    assert actual == pytest.approx(expected, abs=1e-3)


def test_loss_is_monotone_non_increasing_in_rx_height():
    prev = float("inf")
    for h_rx in [0.0, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 14.0, 14.9]:
        v = clutter_loss_saalos(200.0, 15.0, 30.0, h_rx, 0.0, 0, 1000.0)
        assert v <= prev + 1e-9, f"non-monotone at h_rx={h_rx}: {v} > {prev}"
        prev = v


def test_long_distance_caps_at_max():
    v = clutter_loss_saalos(100000.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    assert v == MAX_CLUTTER_LOSS


def test_frequency_changes_loss():
    f300 = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 300.0)
    f1000 = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    f3000 = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 3000.0)
    assert f300 == pytest.approx(9.336117, abs=1e-3)
    assert f1000 == pytest.approx(9.301259, abs=1e-3)
    assert f3000 == pytest.approx(9.269451, abs=1e-3)


def test_polarization_accepted_for_all_codes():
    for pol in (0, 1, 2):
        v = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, pol, 1000.0)
        assert 0.0 <= v <= MAX_CLUTTER_LOSS


def test_negative_arte_clamped_to_zero():
    v = clutter_loss_saalos(1.0, 0.5, 0.1, 0.001, 1000.0, 0, 10.0)
    assert v >= 0.0


import numpy as np
from clutter.saalos import clutter_loss_saalos_vec


def test_vec_matches_scalar_h_pol():
    ds = np.array([100.0, 150.0, 200.0])
    cch = 15.0
    h_tx = 30.0
    h_rx = 2.0
    h_gnd = 0.0
    f = 1000.0
    expected = np.array([
        clutter_loss_saalos(d, cch, h_tx, h_rx, h_gnd, 0, f) for d in ds
    ])
    vec = clutter_loss_saalos_vec(ds, cch, h_tx, h_rx, h_gnd, 0, f)
    np.testing.assert_allclose(vec, expected, atol=1e-6)


def test_vec_zero_conditions():
    d = np.array([0.0, 1000.0, 1000.0])
    cch = np.array([15.0, 0.0, 15.0])
    h_rx = np.array([2.0, 2.0, 20.0])
    vec = clutter_loss_saalos_vec(d, cch, 30.0, h_rx, 0.0, 0, 1000.0)
    np.testing.assert_allclose(vec, 0.0, atol=1e-10)


def test_vec_scalar_inputs():
    v = clutter_loss_saalos_vec(200.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    expected = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    assert v == pytest.approx(expected, abs=1e-6)


def test_vec_below_clutter():
    cch = 15.0
    h_tx_vals = np.array([5.0, 10.0])
    vec = clutter_loss_saalos_vec(1000.0, cch, h_tx_vals, 2.0, 0.0, 0, 1000.0)
    for i, h_tx in enumerate(h_tx_vals):
        expected = clutter_loss_saalos(1000.0, cch, h_tx, 2.0, 0.0, 0, 1000.0)
        assert vec[i] == pytest.approx(expected, abs=1e-4)


def test_vec_monotone_in_rx_height():
    h_rx_vals = np.linspace(0.5, 14.5, 15)
    vec = clutter_loss_saalos_vec(200.0, 15.0, 30.0, h_rx_vals, 0.0, 0, 1000.0)
    for i in range(1, len(vec)):
        assert vec[i] <= vec[i - 1] + 1e-9


def test_vec_matches_scalar_above_clutter_various_distances():
    params = [
        (100.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0),
        (500.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0),
        (1000.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0),
        (5000.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0),
        (200.0, 20.0, 40.0, 3.0, 0.0, 1, 2400.0),
        (200.0, 20.0, 40.0, 3.0, 0.0, 2, 2400.0),
    ]
    for d, cch, htx, hrx, hgnd, pol, f in params:
        scalar = clutter_loss_saalos(d, cch, htx, hrx, hgnd, pol, f)
        vec = clutter_loss_saalos_vec(d, cch, htx, hrx, hgnd, pol, f)
        assert float(vec) == pytest.approx(scalar, abs=1e-6), (
            f"Mismatch at d={d}, cch={cch}, htx={htx}, hrx={hrx}, pol={pol}, f={f}"
        )