# -*- coding: utf-8 -*-
"""Helpers for deriving coverage metrics from a computed raster grid."""

import numpy as np

try:
    from .elevation import haversine_m
except ImportError:  # pragma: no cover - direct test imports use module mode
    from elevation import haversine_m


def summarize_coverage_grid(
    prx_grid,
    tx_lat,
    tx_lon,
    min_lat,
    max_lat,
    min_lon,
    max_lon,
    rx_sensitivity_dbm,
):
    """Summarize usable-distance metrics from a received-power raster."""
    n_rows, n_cols = prx_grid.shape
    lat_step = (max_lat - min_lat) / n_rows
    lon_step = (max_lon - min_lon) / n_cols
    usable_distances_km = []

    for row in range(n_rows):
        cell_lat = max_lat - ((row + 0.5) * lat_step)
        for col in range(n_cols):
            cell_value = prx_grid[row, col]
            if np.isnan(cell_value) or cell_value < rx_sensitivity_dbm:
                continue

            cell_lon = min_lon + ((col + 0.5) * lon_step)
            distance_km = haversine_m(tx_lat, tx_lon, cell_lat, cell_lon) / 1000.0
            usable_distances_km.append(distance_km)

    if not usable_distances_km:
        return {
            "usable_cell_count": 0,
            "min_distance_km": 0.0,
            "max_distance_km": 0.0,
            "average_distance_km": 0.0,
        }

    usable_arr = np.asarray(usable_distances_km, dtype=np.float64)
    return {
        "usable_cell_count": int(usable_arr.size),
        "min_distance_km": float(usable_arr.min()),
        "max_distance_km": float(usable_arr.max()),
        "average_distance_km": float(usable_arr.mean()),
    }
