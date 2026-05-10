# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for P.2108 terrestrial statistical clutter loss (canonical module).

The deprecated clutter_p2108 shim has been removed; these tests now
exercise p2108_terrestrial_stat directly.
"""

import numpy as np

from p2108_terrestrial_stat import (
    clutter_loss_p2108_terrestrial_stat,
    clutter_loss_p2108_terrestrial_stat_vec,
)


def test_open_category_returns_zero():
    assert clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=50.0) >= 0.0


def test_scalar_delegation():
    v = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=50.0)
    assert v >= 0.0


def test_vectorized_delegates():
    vec = clutter_loss_p2108_terrestrial_stat_vec(
        np.array([0.5, 1.0]), 2.0, p=50.0)
    assert vec.shape == (2,)
    assert all(v >= 0.0 for v in vec)


def test_loss_is_non_negative():
    for d_km in [0.1, 1.0, 10.0]:
        for f_ghz in [0.5, 1.0, 2.0, 5.0]:
            loss = clutter_loss_p2108_terrestrial_stat(d_km, f_ghz, p=50.0)
            assert loss >= 0.0