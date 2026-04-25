# -*- coding: utf-8 -*-
"""Unit tests for raster-derived coverage summary metrics."""

import numpy as np

from coverage_summary import summarize_coverage_grid


def test_summarize_coverage_grid_reports_distances_for_usable_cells():
    prx_grid = np.array(
        [
            [-120.0, -95.0, -120.0],
            [-95.0, -80.0, -95.0],
            [-120.0, -95.0, -120.0],
        ]
    )
    summary = summarize_coverage_grid(
        prx_grid=prx_grid,
        tx_lat=0.0,
        tx_lon=0.0,
        min_lat=-0.01,
        max_lat=0.01,
        min_lon=-0.01,
        max_lon=0.01,
        rx_sensitivity_dbm=-100.0,
    )
    assert summary["usable_cell_count"] == 5
    assert summary["max_distance_km"] > 0.0
    assert summary["average_distance_km"] > 0.0


def test_summarize_coverage_grid_handles_no_service_case():
    prx_grid = np.full((2, 2), -130.0)
    summary = summarize_coverage_grid(
        prx_grid=prx_grid,
        tx_lat=0.0,
        tx_lon=0.0,
        min_lat=-0.01,
        max_lat=0.01,
        min_lon=-0.01,
        max_lon=0.01,
        rx_sensitivity_dbm=-100.0,
    )
    assert summary["usable_cell_count"] == 0
    assert summary["min_distance_km"] == 0.0
    assert summary["max_distance_km"] == 0.0
    assert summary["average_distance_km"] == 0.0
