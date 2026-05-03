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

from .constants import METERS_PER_DEGREE_LAT, EARTH_RADIUS_M

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
    from .clutter import compute_terminal_clutter_losses

    lat_per_m = 1.0 / METERS_PER_DEGREE_LAT
    lon_per_m = 1.0 / (METERS_PER_DEGREE_LAT * max(math.cos(math.radians(tx_lat)), 0.01))
    dlat = (lats[:, np.newaxis] - tx_lat) / lat_per_m
    dlon = (lons[np.newaxis, :] - tx_lon) / lon_per_m
    dist_grid = _haversine_grid(tx_lat, tx_lon, lats, lons)
    bearing_grid = (np.degrees(np.arctan2(dlon, dlat)) + 360.0) % 360.0

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
            rx_clutter = compute_terminal_clutter_losses(
                tx_lat=tx_lat,
                tx_lon=tx_lon,
                rx_lat=float(lats[i]),
                rx_lon=float(lons[j]),
                frequency_mhz=f_mhz,
                enabled=clutter_enabled,
                land_cover_grid=clutter_grid,
                tx_override="open",
                rx_override=rx_clutter_override,
            )
            tasks.append(
                (
                    i,
                    j,
                    float(lats[i]),
                    float(lons[j]),
                    modeled_d_m,
                    b,
                    step_m,
                    n_pts,
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
                    antenna_config,
                    rx_gain_dbi,
                    tx_clutter_loss_db,
                    rx_clutter.rx_loss_db,
                )
            )
    return tasks