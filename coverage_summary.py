# -*- coding: utf-8 -*-
"""Helpers for deriving coverage metrics from a computed raster grid."""

import numpy as np


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

    # Build cell center coordinate arrays
    cell_lats = max_lat - ((np.arange(n_rows) + 0.5) * lat_step)  # (n_rows,)
    cell_lons = min_lon + ((np.arange(n_cols) + 0.5) * lon_step)  # (n_cols,)

    # Vectorized haversine distance computation — broadcast to 2D grid
    R = 6371000.0
    lat1_r = np.radians(tx_lat)
    lon1_r = np.radians(tx_lon)
    lat2_r = np.radians(cell_lats)[:, np.newaxis]  # (n_rows, 1)
    lon2_r = np.radians(cell_lons)[np.newaxis, :]  # (1, n_cols)

    dphi = lat2_r - lat1_r
    dlam = lon2_r - lon1_r
    a = np.sin(dphi / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlam / 2) ** 2
    dist_grid_km = (2 * R * np.arcsin(np.sqrt(a))) / 1000.0  # (n_rows, n_cols)

    # Mask: usable cells above sensitivity
    usable_mask = (~np.isnan(prx_grid)) & (prx_grid >= rx_sensitivity_dbm)
    usable_distances = dist_grid_km[usable_mask]

    if usable_distances.size == 0:
        return {
            "usable_cell_count": 0,
            "min_distance_km": 0.0,
            "max_distance_km": 0.0,
            "average_distance_km": 0.0,
        }

    return {
        "usable_cell_count": int(usable_distances.size),
        "min_distance_km": float(usable_distances.min()),
        "max_distance_km": float(usable_distances.max()),
        "average_distance_km": float(usable_distances.mean()),
    }
