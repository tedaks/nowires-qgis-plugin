# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for zero-division guard in summarize_coverage_grid (v1.5.7 fix #17).

Before v1.5.7, summarize_coverage_grid raised ZeroDivisionError when
prx_grid.shape yielded zero rows or columns. The fix returns the existing
zero-count summary dict early when n_rows or n_cols is 0.
"""

import numpy as np


def test_summarize_coverage_grid_zero_rows():
    """Empty grid with 0 rows must return zero-count summary, not raise."""
    from NoWires.coverage_summary import summarize_coverage_grid

    result = summarize_coverage_grid(
        np.array([], dtype=np.float32).reshape(0, 0),
        0, 0, -1, 1, -1, 1, -100,
    )
    assert result["usable_cell_count"] == 0
    assert result["min_distance_km"] == 0.0
    assert result["max_distance_km"] == 0.0
    assert result["average_distance_km"] == 0.0


def test_summarize_coverage_grid_zero_cols():
    """Empty grid with 0 cols must return zero-count summary, not raise."""
    from NoWires.coverage_summary import summarize_coverage_grid

    grid = np.array([], dtype=np.float32).reshape(5, 0)
    result = summarize_coverage_grid(
        grid, 0, 0, -1, 1, -1, 1, -100,
    )
    assert result["usable_cell_count"] == 0


def test_summarize_coverage_grid_normal_grid():
    """Normal grid must still produce valid results."""
    from NoWires.coverage_summary import summarize_coverage_grid

    prx = np.full((10, 10), -50.0, dtype=np.float32)
    result = summarize_coverage_grid(
        prx, 0, 0, -0.05, 0.05, -0.05, 0.05, -100.0,
    )
    assert result["usable_cell_count"] > 0
    assert result["min_distance_km"] >= 0