# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np


def test_dist_grid_km_nan_where_prx_nan():
    from NoWires.coverage.summary import summarize_coverage_grid
    prx_grid = np.array([[-50.0, np.nan], [-60.0, np.nan]], dtype=np.float32)
    result = summarize_coverage_grid(
        prx_grid=prx_grid, tx_lat=14.5, tx_lon=121.0,
        rx_sensitivity_dbm=-100.0,
        min_lat=14.0, max_lat=14.5, min_lon=121.0, max_lon=121.5,
    )
    assert result["min_distance_km"] > 0, (
        "min_distance_km must be > 0 for valid coverage pixels")
    assert not np.isnan(result["min_distance_km"]), (
        "min_distance_km must not be NaN when usable pixels exist")
    assert result["usable_cell_count"] == 2, (
        "Both valid prx pixels should be counted above sensitivity")