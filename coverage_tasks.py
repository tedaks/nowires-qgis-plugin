# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
        email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import math

import numpy as np

from .clutter import CLUTTER_LOSS_DB
from .constants import EARTH_RADIUS_M
from .coverage_pool import _CoverageTask

_MIN_COVERAGE_DISTANCE_M = 1.0


def _haversine_grid(tx_lat, tx_lon, lats, lons):
    """Vectorized haversine distance from TX to every grid cell center, in metres."""
    R = EARTH_RADIUS_M
    lat1_r = math.radians(tx_lat)
    lon1_r = math.radians(tx_lon)
    lat2_r = np.radians(lats)[:, np.newaxis]
    lon2_r = np.radians(lons)[np.newaxis, :]
    dphi = lat2_r - lat1_r
    dlam = lon2_r - lon1_r
    a = np.sin(dphi / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlam / 2) ** 2
    a = np.clip(a, 0.0, 1.0)
    return 2 * R * np.arcsin(np.sqrt(a))


def _bearing_grid(tx_lat, tx_lon, lats, lons):
    """Vectorized forward azimuth (bearing) from TX to every grid cell center, in degrees."""
    lat1_r = math.radians(tx_lat)
    lon1_r = math.radians(tx_lon)
    lat2_r = np.radians(lats)[:, np.newaxis]
    lon2_r = np.radians(lons)[np.newaxis, :]
    dlon = lon2_r - lon1_r
    x = np.sin(dlon) * np.cos(lat2_r)
    y = np.cos(lat1_r) * np.sin(lat2_r) - np.sin(lat1_r) * np.cos(lat2_r) * np.cos(dlon)
    return (np.degrees(np.arctan2(x, y)) + 360.0) % 360.0


def _coverage_axis_centers(min_value, max_value, size):
    """Return evenly spaced cell centers for a raster extent."""
    if size <= 0:
        return np.asarray([], dtype=np.float64)
    step = (max_value - min_value) / float(size)
    return min_value + ((np.arange(size, dtype=np.float64) + 0.5) * step)


def build_coverage_tasks(
    tx_lat,
    tx_lon,
    radius_m,
    grid_size,
    profile_step_m,
    max_profile_pts,
    tx_h_m,
    rx_h_m,
    climate,
    N0,
    f_mhz,
    polarization,
    epsilon,
    sigma,
    time_pct,
    location_pct,
    situation_pct,
    eirp_dbm,
    rx_gain_dbi,
    antenna_config,
    clutter_enabled,
    clutter_grid,
    tx_clutter_loss_db,
    rx_clutter_override,
    lats,
    lons,
):
    dist_grid = _haversine_grid(tx_lat, tx_lon, lats, lons)
    bearing_grid = _bearing_grid(tx_lat, tx_lon, lats, lons)

    n_rows_lat = len(lats)
    n_cols_lon = len(lons)
    if clutter_enabled and clutter_grid is not None and rx_clutter_override is None:
        rx_clutter_loss_grid = clutter_grid.sample_category_grid(lats, lons)
    elif clutter_enabled and rx_clutter_override is not None:
        override_loss = CLUTTER_LOSS_DB.get(rx_clutter_override, 0.0)
        rx_clutter_loss_grid = np.full((n_rows_lat, n_cols_lon), override_loss, dtype=np.float64)
    elif clutter_enabled and clutter_grid is None:
        fallback_loss = CLUTTER_LOSS_DB.get(rx_clutter_override or "open", 0.0)
        rx_clutter_loss_grid = np.full((n_rows_lat, n_cols_lon), fallback_loss, dtype=np.float64)
    else:
        rx_clutter_loss_grid = None

    tasks = []
    for i in range(grid_size):
        for j in range(grid_size):
            d_m = float(dist_grid[i, j])
            if d_m > radius_m:
                continue
            modeled_d_m = max(d_m, _MIN_COVERAGE_DISTANCE_M)
            b = float(bearing_grid[i, j])
            n_pts = max(
                3, min(int(round(modeled_d_m / profile_step_m)) + 1, max_profile_pts)
            )
            step_m = modeled_d_m / (n_pts - 1)
            rx_clutter_db = float(rx_clutter_loss_grid[i, j]) if rx_clutter_loss_grid is not None else 0.0
            tasks.append(
                _CoverageTask(
                    i=i,
                    j=j,
                    target_lat=float(lats[i]),
                    target_lon=float(lons[j]),
                    dist_m=modeled_d_m,
                    bearing=b,
                    step_m=step_m,
                    n_pts=n_pts,
                    tx_h_m=tx_h_m,
                    rx_h_m=rx_h_m,
                    climate=climate,
                    N0=N0,
                    f_mhz=f_mhz,
                    polarization=polarization,
                    epsilon=epsilon,
                    sigma=sigma,
                    time_pct=time_pct,
                    location_pct=location_pct,
                    situation_pct=situation_pct,
                    eirp_dbm=eirp_dbm,
                    antenna_config=antenna_config,
                    rx_gain_dbi=rx_gain_dbi,
                    clutter_tx_db=tx_clutter_loss_db,
                    clutter_rx_db=rx_clutter_db,
                )
            )
    return tasks