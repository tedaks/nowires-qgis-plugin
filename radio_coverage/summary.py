# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
        email                : tedaks@gmail.com
 ***************************************************************************/

 Licensed under the MIT License; see the LICENSE file for the full text.


Helpers for deriving coverage metrics from a computed raster grid.
"""

import numpy as np

from NoWires.constants import COVERAGE_NODATA, EARTH_RADIUS_M


def summarize_coverage_grid(
    prx_grid,
    tx_lat,
    tx_lon,
    min_lat,
    max_lat,
    min_lon,
    max_lon,
    rx_sensitivity_dbm,
) -> dict:
    """Summarize usable-distance metrics from a received-power raster."""
    prx_grid = np.where(np.isfinite(prx_grid) & (prx_grid != COVERAGE_NODATA), prx_grid, np.nan)
    n_rows, n_cols = prx_grid.shape
    if n_rows == 0 or n_cols == 0:
        return {
            "usable_cell_count": 0,
            "min_distance_km": 0.0,
            "max_distance_km": 0.0,
            "average_distance_km": 0.0,
        }
    lat_step = (max_lat - min_lat) / n_rows
    lon_step = (max_lon - min_lon) / n_cols

    # Build cell center coordinate arrays
    cell_lats = max_lat - ((np.arange(n_rows) + 0.5) * lat_step)  # (n_rows,)
    cell_lons = min_lon + ((np.arange(n_cols) + 0.5) * lon_step)  # (n_cols,)

    # Vectorized haversine distance computation — broadcast to 2D grid
    R = EARTH_RADIUS_M
    lat1_r = np.radians(tx_lat)
    lon1_r = np.radians(tx_lon)
    lat2_r = np.radians(cell_lats)[:, np.newaxis]  # (n_rows, 1)
    lon2_r = np.radians(cell_lons)[np.newaxis, :]  # (1, n_cols)

    dphi = lat2_r - lat1_r
    dlam = lon2_r - lon1_r
    a = np.sin(dphi / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlam / 2) ** 2
    a = np.clip(a, 0.0, 1.0)
    dist_grid_km = (2 * R * np.arcsin(np.sqrt(a))) / 1000.0  # (n_rows, n_cols)
    dist_grid_km = np.where(np.isnan(prx_grid), np.nan, dist_grid_km)

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
