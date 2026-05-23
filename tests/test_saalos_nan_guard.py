# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
import math

import numpy as np

from NoWires.clutter.saalos import clutter_loss_saalos, clutter_loss_saalos_vec


def test_scalar_small_cch_returns_finite():
    result = clutter_loss_saalos(1000.0, 0.001, 0.001, 0.0005, 0.0, 0, 1000.0)
    assert not math.isnan(result), "scalar returned NaN for small cch"
    assert math.isfinite(result), f"scalar returned non-finite: {result}"


def test_scalar_cch_equals_htx_returns_finite():
    result = clutter_loss_saalos(1000.0, 10.0, 10.0, 2.0, 0.0, 0, 1000.0)
    assert not math.isnan(result), "scalar returned NaN when cch == htx"
    assert math.isfinite(result), f"scalar returned non-finite: {result}"


def test_vec_small_cch_returns_finite():
    d = np.array([1000.0, 500.0])
    cch = np.array([0.001, 0.001])
    htx = np.array([0.001, 0.001])
    hrx = np.array([0.0005, 0.0005])
    result = clutter_loss_saalos_vec(d, cch, htx, hrx, 0.0, 0, 1000.0)
    assert np.all(np.isfinite(result)), f"vec returned non-finite: {result}"


def test_vec_cch_equals_htx_returns_finite():
    d = np.array([1000.0, 500.0])
    cch = np.array([10.0, 15.0])
    htx = np.array([10.0, 15.0])
    hrx = np.array([2.0, 3.0])
    result = clutter_loss_saalos_vec(d, cch, htx, hrx, 0.0, 0, 1000.0)
    assert np.all(np.isfinite(result)), f"vec returned non-finite when cch == htx: {result}"


def test_scalar_near_equal_cch_htx_returns_finite():
    result = clutter_loss_saalos(200.0, 5.0, 4.9999, 2.0, 0.0, 0, 1000.0)
    assert not math.isnan(result)
    assert math.isfinite(result)


def test_vec_near_equal_cch_htx_returns_finite():
    d = np.array([200.0])
    cch = np.array([5.0])
    htx = np.array([4.9999])
    hrx = np.array([2.0])
    result = clutter_loss_saalos_vec(d, cch, htx, hrx, 0.0, 0, 1000.0)
    assert np.all(np.isfinite(result))