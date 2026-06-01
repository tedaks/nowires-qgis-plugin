# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
import numpy as np
import pytest

from clutter.p833 import clutter_loss_p833, clutter_loss_p833_vec

CCH = 12.0
H_RX_BELOW = 2.0
F_900 = 900.0
F_1800 = 1800.0
F_2600 = 2600.0


# ---------------------------------------------------------------------------
# Canopy boundary and above-canopy behaviour
# ---------------------------------------------------------------------------

def test_zero_when_rx_at_canopy():
    assert clutter_loss_p833(CCH, CCH, F_900) == 0.0


def test_zero_when_rx_above_canopy():
    assert clutter_loss_p833(CCH, CCH + 1.0, F_900) == 0.0


def test_positive_loss_below_canopy():
    result = clutter_loss_p833(CCH, H_RX_BELOW, F_900)
    assert result > 0.0


# ---------------------------------------------------------------------------
# Formula: Am = 1.37 * f^0.42
# ---------------------------------------------------------------------------

def test_am_reference_900mhz():
    expected = 1.37 * (F_900 ** 0.42)
    result = clutter_loss_p833(CCH, H_RX_BELOW, F_900)
    assert result == pytest.approx(expected, rel=1e-9)


def test_am_reference_1800mhz():
    expected = 1.37 * (F_1800 ** 0.42)
    result = clutter_loss_p833(CCH, H_RX_BELOW, F_1800)
    assert result == pytest.approx(expected, rel=1e-9)


def test_increases_with_frequency():
    loss_450 = clutter_loss_p833(CCH, H_RX_BELOW, 450.0)
    loss_900 = clutter_loss_p833(CCH, H_RX_BELOW, F_900)
    loss_1800 = clutter_loss_p833(CCH, H_RX_BELOW, F_1800)
    loss_2600 = clutter_loss_p833(CCH, H_RX_BELOW, F_2600)
    assert loss_450 < loss_900 < loss_1800 < loss_2600


# ---------------------------------------------------------------------------
# No MAX_CLUTTER_LOSS cap
# ---------------------------------------------------------------------------

def test_no_max_clutter_loss_cap():
    # At 2600 MHz Am ≈ 37 dB — must not be capped at 22 dB.
    result = clutter_loss_p833(CCH, H_RX_BELOW, F_2600)
    assert result > 22.0


# ---------------------------------------------------------------------------
# Scalar / vectorised agreement
# ---------------------------------------------------------------------------

def test_scalar_vec_agreement():
    scalar = clutter_loss_p833(CCH, H_RX_BELOW, F_900)
    vec = clutter_loss_p833_vec(CCH, H_RX_BELOW, F_900)
    assert float(vec) == scalar


def test_vec_broadcasts():
    cch_arr = np.array([10.0, 12.0, 15.0])
    hrx_arr = np.array([1.0, 2.0, 3.0])
    f_arr = np.array([450.0, 900.0, 1800.0])
    result = clutter_loss_p833_vec(cch_arr, hrx_arr, f_arr)
    assert result.shape == (3,)
    for i in range(3):
        expected = clutter_loss_p833(float(cch_arr[i]), float(hrx_arr[i]), float(f_arr[i]))
        assert result[i] == pytest.approx(expected, rel=1e-9)


def test_vec_above_canopy_returns_zero():
    # Mix of below-canopy and above-canopy pixels
    cch = np.array([12.0, 12.0, 12.0])
    hrx = np.array([2.0, 12.0, 15.0])
    result = clutter_loss_p833_vec(cch, hrx, 900.0)
    assert result[0] > 0.0
    assert result[1] == 0.0
    assert result[2] == 0.0
