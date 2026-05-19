# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for haversine numerical stability (v1.5.7 fix #1).

Before v1.5.7, coverage_summary._compute_grid_summary computed
``a = sin²(dφ/2) + cos(φ1)cos(φ2)sin²(dλ/2)`` without clipping,
so FP rounding could push ``a`` slightly above 1.0 (most likely at
antipodal or near-zero distances) and ``arcsin(sqrt(a))`` would
produce NaN. The twin in coverage_tasks._haversine_grid already
clipped; this aligns the two.
"""

import numpy as np


def test_haversine_clip_prevents_nan_at_antipodes():
    """haversine distance must not produce NaN for antipodal points."""
    from NoWires.coverage.summary import summarize_coverage_grid

    tx_lat, tx_lon = 0.0, 0.0
    min_lat, max_lat = -89.0, 89.0
    min_lon, max_lon = -179.0, 179.0
    rx_sens = -100.0
    prx = np.full((180, 360), -50.0, dtype=np.float32)
    result = summarize_coverage_grid(
        prx, tx_lat, tx_lon, min_lat, max_lat, min_lon, max_lon, rx_sens
    )
    assert result["usable_cell_count"] > 0
    assert not np.isnan(result["average_distance_km"])


def test_haversine_clip_prevents_nan_at_coincident_points():
    """haversine distance must not produce NaN when TX equals cell center."""
    from NoWires.coverage.summary import summarize_coverage_grid

    tx_lat, tx_lon = 45.0, 10.0
    prx = np.full((5, 5), -50.0, dtype=np.float32)
    result = summarize_coverage_grid(
        prx, tx_lat, tx_lon, 44.9, 45.1, 9.9, 10.1, -100.0
    )
    assert result["min_distance_km"] >= 0.0
    assert not np.isnan(result["min_distance_km"])