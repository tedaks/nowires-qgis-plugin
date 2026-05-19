# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for build_obstruction_data sorting by deficit, not height.

Before the fix, peaks.sort(key=lambda i: terrain_bulge[i]) sorted by
terrain height, not Fresnel penetration deficit. With more than 5
obstructions, the most obstructive peaks could be omitted.
"""
import numpy as np
from p2p.chart_format import build_obstruction_data


def test_obstruction_data_sorted_by_deficit():
    """Obstructions must be sorted by deficit (highest first), not terrain height."""
    d_km = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    terrain_bulge = np.array([10, 12, 15, 25, 30, 28, 20, 14, 13, 11], dtype=float)
    los_h = np.array([20, 22, 24, 26, 35, 30, 22, 18, 16, 14], dtype=float)
    fresnel_r = np.array([5, 5, 5, 5, 5, 5, 5, 5, 5, 5], dtype=float)

    result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
    deficits = [item[5] for item in result]
    assert deficits == sorted(deficits, reverse=True), (
        "Obstructions must be sorted by deficit descending, got {}".format(deficits)
    )


def test_obstruction_data_returns_six_element_tuples():
    """Each return tuple must be (idx, d_km, terrain_bulge, los_h, fresnel_r, deficit)."""
    d_km = np.array([0, 1, 2])
    terrain_bulge = np.array([10, 25, 10], dtype=float)
    los_h = np.array([20, 20, 20], dtype=float)
    fresnel_r = np.array([5, 5, 5], dtype=float)

    result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
    for item in result:
        assert len(item) == 6, (
            "Each tuple must have 6 elements (idx, d_km, terrain_bulge, los_h, "
            "fresnel_r, deficit), got {}".format(len(item))
        )