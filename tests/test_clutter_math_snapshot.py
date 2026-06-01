# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Drift-guard snapshot tests for clutter-loss math.

For each of the four clutter / building-entry modules
(p2108_height_gain, p2108_terrestrial_stat, p2109_bel, p833)
this file pins a small grid of (inputs -> output) tuples and asserts
math.isclose against them with rel_tol=1e-9.

These are SELF-CAPTURED snapshots: the expected values are what the
current implementation produces, not values from the ITU-R worked
examples or any other authoritative source. Their purpose is to
catch *accidental coefficient drift* between releases (a fat-fingered
constant, a refactor that subtly changes a formula) that would
otherwise sneak past the existing property tests.

They do NOT validate that the implementation is correct against the
spec. Spec validation is the job of the existing per-module tests
(test_p2108_height_gain.py, test_p2108_terrestrial_stat.py,
test_p2109_bel.py, test_clutter_p833.py).

If an intentional change to a formula causes one of these to fail,
re-capture the snapshot by re-running the small generator at the
bottom of this file's docstring.
"""

import math

import pytest

from clutter.p833 import clutter_loss_p833
from clutter.p2108_height_gain import height_gain_loss
from clutter.p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat
from clutter.p2109_bel import building_entry_loss


_REL_TOL = 1e-9
_ABS_TOL = 1e-12  # needed for the 0.0 early-return cases


# (h_m, f_ghz, category, w_s_m) -> dB
_HEIGHT_GAIN_SNAPSHOTS = [
    ((1.5, 0.9, "urban", 27.0), 25.079434470662733),
    ((10.0, 0.9, "urban", 27.0), 20.107750613258425),
    ((1.5, 2.4, "suburban", 27.0), 23.00921125547878),
    ((5.0, 0.3, "dense_rural", 27.0), 5.586560349642717),
    ((1.5, 1.8, "vegetation", 27.0), 25.599035716154972),
    ((1.5, 0.05, "urban", 27.0), 12.72431915155039),    # low-VHF edge
    ((1.5, 3.0, "urban", 27.0), 30.333483065046316),    # upper bound
    ((1.5, 0.9, "open", 27.0), 0.0),                    # early-return 0
]


# (d_km, f_ghz, p) -> dB
_TERRESTRIAL_STAT_SNAPSHOTS = [
    ((1.0, 0.9, 50.0), 24.495386947731937),
    ((2.0, 0.9, 50.0), 24.54064563301074),     # near distance cap
    ((5.0, 0.9, 50.0), 24.54064563301074),     # past cap (same as 2 km)
    ((1.0, 2.4, 50.0), 28.61590825344947),
    ((1.0, 5.0, 90.0), 36.88764947446009),     # above 3 GHz, high percentile
    ((0.5, 1.0, 10.0), 17.546361051280705),    # low percentile
    ((1.5, 0.6, 50.0), 22.77763262815872),
    ((1.5, 0.6, 99.0), 32.0885407117147),      # upper percentile tail
]


# (f_ghz, building_type, theta_deg, p) -> dB
_BEL_SNAPSHOTS = [
    ((0.9, "traditional", 0.0, 50.0), 14.241983750040859),
    ((0.9, "traditional", 30.0, 50.0), 19.309776513101752),
    ((0.9, "thermally_efficient", 0.0, 50.0), 31.15572206238062),
    ((2.4, "traditional", 0.0, 50.0), 15.186891055515641),
    ((2.4, "thermally_efficient", 45.0, 90.0), 57.019126046036384),
    ((5.0, "thermally_efficient", 0.0, 50.0), 31.566081972146574),
    ((0.4, "traditional", 0.0, 10.0), 5.740426442643152),
    ((5.0, "traditional", 0.0, 99.0), 41.30289001135238),
]


# (cch_m, h_rx_m, f_mhz) -> dB  (ITU-R P.833-9 §2.1 Am)
_P833_SNAPSHOTS = [
    ((12.0, 2.0, 450.0),  1.37 * (450.0  ** 0.42)),
    ((12.0, 2.0, 900.0),  1.37 * (900.0  ** 0.42)),
    ((12.0, 2.0, 1800.0), 1.37 * (1800.0 ** 0.42)),
    ((12.0, 2.0, 2600.0), 1.37 * (2600.0 ** 0.42)),
    ((12.0, 12.0, 900.0), 0.0),   # h_rx == cch → 0
    ((12.0, 15.0, 900.0), 0.0),   # h_rx > cch  → 0
]


def _assert_close(actual, expected, inputs):
    assert math.isclose(actual, expected, rel_tol=_REL_TOL, abs_tol=_ABS_TOL), (
        f"snapshot drift on inputs={inputs}: got {actual!r}, expected {expected!r}"
    )


@pytest.mark.parametrize("inputs,expected", _HEIGHT_GAIN_SNAPSHOTS)
def test_height_gain_loss_snapshot(inputs, expected):
    h_m, f_ghz, category, w_s_m = inputs
    actual = height_gain_loss(h_m, f_ghz, category, w_s_m)
    _assert_close(actual, expected, inputs)


@pytest.mark.parametrize("inputs,expected", _TERRESTRIAL_STAT_SNAPSHOTS)
def test_terrestrial_stat_snapshot(inputs, expected):
    d_km, f_ghz, p = inputs
    actual = clutter_loss_p2108_terrestrial_stat(d_km, f_ghz, p)
    _assert_close(actual, expected, inputs)


@pytest.mark.parametrize("inputs,expected", _BEL_SNAPSHOTS)
def test_bel_snapshot(inputs, expected):
    f_ghz, btype, theta, p = inputs
    actual = building_entry_loss(f_ghz, btype, theta, p)
    _assert_close(actual, expected, inputs)


@pytest.mark.parametrize("inputs,expected", _P833_SNAPSHOTS)
def test_p833_snapshot(inputs, expected):
    cch, hrx, f = inputs
    actual = clutter_loss_p833(cch, hrx, f)
    _assert_close(actual, expected, inputs)
