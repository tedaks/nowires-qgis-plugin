# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
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

from NoWires.clutter import CLUTTER_LOSS_DB
from NoWires.clutter.advanced import (
    ClutterComponents,
    compute_advanced_loss,
    compute_path_clutter_loss,
)
from NoWires.clutter.categories import legacy_to_advanced_override, remap_simple_category
from NoWires.clutter.resolve import (
    resolve_category_advanced,
)
from NoWires.clutter.context import ClutterLossContext
from NoWires.constants import EARTH_RADIUS_M
from NoWires.radio_coverage.pool import _CoverageTask

_MIN_COVERAGE_DISTANCE_M = 1.0
_DISTANCE_BUCKET_M = 10.0


def _bucket_key(distance_m, rx_ground_m):
    """Quantise continuous per-pixel parameters for LUT lookup."""
    return (round(distance_m / _DISTANCE_BUCKET_M) * _DISTANCE_BUCKET_M,
            round(rx_ground_m, 1))


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
    tx_ground_elev_m=0.0,
    rx_ground_grid=None,
):
    dist_grid = _haversine_grid(tx_lat, tx_lon, lats, lons)
    bearing_grid = _bearing_grid(tx_lat, tx_lon, lats, lons)

    n_rows_lat = len(lats)
    n_cols_lon = len(lons)

    advanced = clutter_context is not None and clutter_context.model == "advanced"

    if advanced and clutter_enabled:
        tx_category, _tx_source = resolve_category_advanced(
            tx_lat, tx_lon, tx_clutter_override, clutter_grid)
        # In coverage mode every grid cell is an RX location, so rx_override
        # correctly applies across the entire grid even though the name suggests
        # a receiver-only parameter.
        rx_category_grid = (
            clutter_grid.sample_category_grid(
                lats, lons, rx_override=rx_clutter_override, context=clutter_context)
            if clutter_grid is not None else np.full(
                (n_rows_lat, n_cols_lon),
                legacy_to_advanced_override(rx_clutter_override or "open"),
                dtype=object,
            )
        )
        rx_clutter_loss_grid = None
        # BEL parameters are uniform across all pixels (same frequency, building
        # type, elevation angle, and percentile), so compute once outside the
        # per-pixel loop instead of redundantly evaluating per pixel.
        bel_db = 0.0
        if clutter_context.bel_enabled:
            from NoWires.clutter.p2109_bel import building_entry_loss
            bel_db = building_entry_loss(
                f_mhz / 1000.0,
                clutter_context.bel_building_type,
                theta_deg=clutter_context.bel_elevation_angle_deg,
                p=clutter_context.percentile,
            )
    elif clutter_enabled and clutter_grid is not None:
        rx_clutter_loss_grid = clutter_grid.sample_category_grid(
            lats, lons, rx_override=rx_clutter_override)
        rx_category_grid = None
    elif clutter_enabled and rx_clutter_override is not None:
        override_loss = CLUTTER_LOSS_DB.get(remap_simple_category(rx_clutter_override), 0.0)
        rx_clutter_loss_grid = np.full((n_rows_lat, n_cols_lon), override_loss, dtype=np.float64)
        rx_category_grid = None
    elif clutter_enabled and clutter_grid is None:
        fallback_loss = CLUTTER_LOSS_DB.get(remap_simple_category(rx_clutter_override or "open"), 0.0)
        rx_clutter_loss_grid = np.full((n_rows_lat, n_cols_lon), fallback_loss, dtype=np.float64)
        rx_category_grid = None
    else:
        rx_clutter_loss_grid = None
        rx_category_grid = None

    # NOTE: This double loop is O(grid_size^2) in Python.  For large grids
    # with clutter enabled, per-pixel compute_advanced_loss calls in
    # advanced mode dominate task generation time.  A LUT keyed on
    # (category, terminal, distance_bucket, ground_bucket) avoids redundant
    # invocations for pixels sharing the same quantised parameters.
    _clutter_lut: dict[tuple[str, ...], ClutterComponents] = {}
    tasks: list[_CoverageTask] = []
    for i in range(grid_size):
        for j in range(grid_size):
            d_m = float(dist_grid[i, j])
            if d_m < _MIN_COVERAGE_DISTANCE_M or d_m > radius_m:
                continue
            b = float(bearing_grid[i, j])
            n_pts = max(
                3, min(int(round(d_m / profile_step_m)) + 1, max_profile_pts)
            )
            step_m = d_m / (n_pts - 1)
            if advanced and rx_category_grid is not None:
                rx_ground_m = (
                    float(rx_ground_grid[i, j]) if rx_ground_grid is not None else 0.0
                )
                bucket = _bucket_key(d_m, rx_ground_m)
                tx_lut_key = ("tx", tx_category, bucket)
                rx_cat = rx_category_grid[i, j]
                rx_lut_key = ("rx", rx_cat, bucket)
                tx_cached = _clutter_lut.get(tx_lut_key)
                rx_cached = _clutter_lut.get(rx_lut_key)
                pixel_ctx = ClutterLossContext(
                    frequency_mhz=f_mhz,
                    distance_m=d_m,
                    tx_height_m=tx_h_m,
                    rx_height_m=rx_h_m,
                    rx_ground_elevation_m=rx_ground_m,
                    tx_ground_elevation_m=tx_ground_elev_m,
                    polarization=polarization,
                    cch_override_m=clutter_context.cch_override_m,
                    model="advanced",
                    percentile=clutter_context.percentile,
                    street_width_m=clutter_context.street_width_m,
                    bel_enabled=False,
                    bel_building_type=clutter_context.bel_building_type,
                    bel_elevation_angle_deg=clutter_context.bel_elevation_angle_deg,
                )
                if tx_cached is None:
                    tx_comp = compute_advanced_loss(tx_category, "tx", pixel_ctx)
                    _clutter_lut[tx_lut_key] = tx_comp
                else:
                    tx_comp = tx_cached
                if rx_cached is None:
                    rx_comp = compute_advanced_loss(rx_cat, "rx", pixel_ctx)
                    _clutter_lut[rx_lut_key] = rx_comp
                else:
                    rx_comp = rx_cached
                # Combine terminal-level and path-level clutter correctly.
                # §3.2 stat_loss must be applied once per path, not summed.
                # SAALOS applied to both endpoints must use the larger
                # value, not be summed.
                path_total = compute_path_clutter_loss(tx_comp, rx_comp)
                # Split total across tx/rx proportional to per-terminal
                # contributions so clutter_tx_db + clutter_rx_db ==
                # path_total and downstream sum remains correct.
                term_sum = tx_comp.terminal_loss_db + rx_comp.terminal_loss_db
                if term_sum > 0.0:
                    tx_clutter_db = path_total * (tx_comp.terminal_loss_db / term_sum)
                    rx_clutter_db = path_total * (rx_comp.terminal_loss_db / term_sum)
                else:
                    # Both terminals zero: split evenly (both will be 0.0).
                    tx_clutter_db = path_total * 0.5
                    rx_clutter_db = path_total * 0.5
                pixel_bel_db = bel_db if clutter_context.bel_enabled else 0.0
            elif rx_clutter_loss_grid is not None:
                tx_clutter_db = tx_clutter_loss_db
                rx_clutter_db = float(rx_clutter_loss_grid[i, j])
                pixel_bel_db = 0.0
            else:
                tx_clutter_db = tx_clutter_loss_db
                rx_clutter_db = 0.0
                pixel_bel_db = 0.0
            tasks.append(
                _CoverageTask(
                    i=i,
                    j=j,
                    target_lat=float(lats[i]),
                    target_lon=float(lons[j]),
                    dist_m=d_m,
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
                    bel_rx_db=pixel_bel_db,
                )
            )
    return tasks
