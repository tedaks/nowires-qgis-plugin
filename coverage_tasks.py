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
from .clutter_advanced import (
    _legacy_to_advanced_override,
    _resolve_category_advanced,
    compute_terminal_clutter_loss,
)
from .clutter_context import ClutterLossContext
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
    clutter_context=None,
    tx_clutter_override=None,
):
    dist_grid = _haversine_grid(tx_lat, tx_lon, lats, lons)
    bearing_grid = _bearing_grid(tx_lat, tx_lon, lats, lons)

    n_rows_lat = len(lats)
    n_cols_lon = len(lons)
    advanced = clutter_context is not None and clutter_context.model == "advanced"

    if advanced and clutter_enabled:
        tx_category, _tx_source = _resolve_category_advanced(
            tx_lat, tx_lon, tx_clutter_override, clutter_grid)
        rx_category_grid = (
            clutter_grid.sample_category_grid(
                lats, lons, rx_override=rx_clutter_override, context=clutter_context)
            if clutter_grid is not None else np.full(
                (n_rows_lat, n_cols_lon),
                _legacy_to_advanced_override(rx_clutter_override or "open"),
                dtype=object,
            )
        )
        rx_clutter_loss_grid = None
    elif clutter_enabled and clutter_grid is not None and rx_clutter_override is None:
        rx_clutter_loss_grid = clutter_grid.sample_category_grid(lats, lons)
        rx_category_grid = None
    elif clutter_enabled and rx_clutter_override is not None:
        override_loss = CLUTTER_LOSS_DB.get(rx_clutter_override, 0.0)
        rx_clutter_loss_grid = np.full((n_rows_lat, n_cols_lon), override_loss, dtype=np.float64)
        rx_category_grid = None
    elif clutter_enabled and clutter_grid is None:
        fallback_loss = CLUTTER_LOSS_DB.get(rx_clutter_override or "open", 0.0)
        rx_clutter_loss_grid = np.full((n_rows_lat, n_cols_lon), fallback_loss, dtype=np.float64)
        rx_category_grid = None
    else:
        rx_clutter_loss_grid = None
        rx_category_grid = None

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
            if advanced and rx_category_grid is not None:
                pixel_ctx = ClutterLossContext(
                    frequency_mhz=f_mhz,
                    distance_m=modeled_d_m,
                    tx_height_m=tx_h_m,
                    rx_height_m=rx_h_m,
                    rx_ground_elevation_m=0.0,
                    polarization=polarization,
                    cch_override_m=clutter_context.cch_override_m,
                    model="advanced",
                    percentile=clutter_context.percentile,
                    street_width_m=clutter_context.street_width_m,
                    bel_enabled=clutter_context.bel_enabled,
                    bel_building_type=clutter_context.bel_building_type,
                    bel_elevation_angle_deg=clutter_context.bel_elevation_angle_deg,
                )
                tx_clutter_db = compute_terminal_clutter_loss(
                    tx_category, "tx", pixel_ctx)
                rx_clutter_db = compute_terminal_clutter_loss(
                    rx_category_grid[i, j], "rx", pixel_ctx)
                if clutter_context.bel_enabled:
                    from .p2109_bel import building_entry_loss
                    rx_bel_db = building_entry_loss(
                        f_mhz / 1000.0,
                        clutter_context.bel_building_type,
                        theta_deg=clutter_context.bel_elevation_angle_deg,
                        p=clutter_context.percentile,
                    )
                    rx_clutter_db += rx_bel_db
            elif rx_clutter_loss_grid is not None:
                tx_clutter_db = tx_clutter_loss_db
                rx_clutter_db = float(rx_clutter_loss_grid[i, j])
            else:
                tx_clutter_db = tx_clutter_loss_db
                rx_clutter_db = 0.0
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
                    clutter_tx_db=tx_clutter_db,
                    clutter_rx_db=rx_clutter_db,
                )
            )
    return tasks
