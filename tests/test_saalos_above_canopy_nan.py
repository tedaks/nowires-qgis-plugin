# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: SAALOS above-canopy NaN guard must return MAX_CLUTTER_LOSS."""

import math

import numpy as np
import pytest

from NoWires.clutter.constants import MAX_CLUTTER_LOSS
from NoWires.clutter.saalos import clutter_loss_saalos, clutter_loss_saalos_vec


def test_scalar_above_canopy_cch_equals_htx():
    """cch == htx in above-canopy branch: must return finite, not NaN."""
    result = clutter_loss_saalos(
        d__meter=1000.0,
        cch__meter=30.0,
        h_tx__meter=30.0,
        h_rx__meter=10.0,
        h_rx_gnd__meter=5.0,
        pol=0,
        f__mhz=900.0,
    )
    assert not math.isnan(result), f"above-canopy returned NaN: {result}"
    assert math.isfinite(result)
    assert 0.0 <= result <= MAX_CLUTTER_LOSS


def test_scalar_above_canopy_very_small_d():
    """Very small distance in above-canopy: must return finite, not NaN."""
    result = clutter_loss_saalos(
        d__meter=1.0,
        cch__meter=5.0,
        h_tx__meter=20.0,
        h_rx__meter=2.0,
        h_rx_gnd__meter=1.0,
        pol=1,
        f__mhz=150.0,
    )
    assert not math.isnan(result), f"above-canopy small d returned NaN: {result}"
    assert math.isfinite(result)
    assert 0.0 <= result <= MAX_CLUTTER_LOSS


def test_vec_above_canopy_cch_equals_htx():
    """Vector path: cch == htx in above-canopy must be finite."""
    d = np.array([1000.0, 500.0])
    cch = np.array([30.0, 25.0])
    htx = np.array([30.0, 25.0])
    hrx = np.array([10.0, 8.0])
    result = clutter_loss_saalos_vec(d, cch, htx, hrx, 5.0, 0, 900.0)
    assert np.all(np.isfinite(result)), f"vec above-canopy returned non-finite: {result}"
    assert np.all(result >= 0.0)
    assert np.all(result <= MAX_CLUTTER_LOSS)