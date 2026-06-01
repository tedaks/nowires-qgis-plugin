# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

import logging

import numpy as np

from NoWires.antenna import antenna_config_from_values
from NoWires.clutter import compute_terminal_clutter_losses
from NoWires.clutter.context import ClutterLossContext, build_initial_clutter_context, ClutterModel, BuildingType  # noqa: F401
from NoWires.radio_coverage.pool import (  # noqa: F401
    CoverageResult, log_coverage_failures, should_use_multiprocessing,
    _itm_worker, _make_shared_grid,
)
from NoWires.radio_coverage._executor import execute_coverage_tasks
from NoWires.radio_coverage.tasks import _coverage_axis_centers, build_coverage_tasks
from NoWires.geo_bounds import coverage_bounds
from NoWires.constants import BYTES_PER_MEBIBYTE
from NoWires.defaults import DEFAULT_N0, DEFAULT_EPSILON, DEFAULT_SIGMA

logger = logging.getLogger(__name__)


def _build_clutter_context(clutter_enabled, clutter_context, f_mhz, tx_h_m, rx_h_m,
                           cch_override_m, clutter_model,
                           clutter_percentile, street_width_m, bel_enabled, bel_building_type,
                           bel_elevation_angle_deg):
    if clutter_context is None and bel_enabled and not clutter_enabled:
        return build_initial_clutter_context(
            frequency_mhz=f_mhz, tx_height_m=tx_h_m, rx_height_m=rx_h_m,
            cch_override_m=cch_override_m, model="simple",
            percentile=clutter_percentile, street_width_m=street_width_m,
            bel_enabled=bel_enabled, bel_building_type=bel_building_type,
            bel_elevation_angle_deg=bel_elevation_angle_deg)
    if clutter_enabled and clutter_context is None:
        return build_initial_clutter_context(
            frequency_mhz=f_mhz, tx_height_m=tx_h_m, rx_height_m=rx_h_m,
            cch_override_m=cch_override_m, model=clutter_model,
            percentile=clutter_percentile, street_width_m=street_width_m,
            bel_enabled=bel_enabled, bel_building_type=bel_building_type,
            bel_elevation_angle_deg=bel_elevation_angle_deg)
    return clutter_context


def _compute_tx_clutter_loss(tx_lat, tx_lon, tx_clutter_loss_db, f_mhz,
                             clutter_enabled, clutter_grid, tx_clutter_override,
                             rx_clutter_override, clutter_context):
    if tx_clutter_loss_db is not None:
        return tx_clutter_loss_db
    # Advanced mode recomputes TX clutter per pixel (P.2108 §3.2 is distance-dependent),
    # so the distance=0 precompute would be discarded. Skip it.
    if clutter_context is not None and clutter_context.model == "advanced":
        return 0.0
    tx_clutter = compute_terminal_clutter_losses(
        tx_lat=tx_lat, tx_lon=tx_lon, rx_lat=tx_lat, rx_lon=tx_lon,
        frequency_mhz=f_mhz, enabled=clutter_enabled,
        land_cover_grid=clutter_grid, tx_override=tx_clutter_override,
        rx_override=rx_clutter_override, context=clutter_context,
    )
    return tx_clutter.tx_loss_db


def compute_coverage(
    elev_grid, tx_lat, tx_lon, tx_h_m, rx_h_m, f_mhz,
    grid_size=192, radius_km=50.0, profile_step_m=250.0, max_profile_pts=75,
    tx_power_dbm=43.0, tx_gain_dbi=8.0, rx_gain_dbi=2.0, cable_loss_db=2.0,
    rx_sensitivity_dbm=-100.0, antenna_az_deg=None, antenna_beamwidth_deg=360.0,
    polarization=0, climate=1, N0=DEFAULT_N0, epsilon=DEFAULT_EPSILON, sigma=DEFAULT_SIGMA,
    time_pct=50.0, location_pct=50.0, situation_pct=50.0, antenna_preset=0,
    antenna_front_back_db=25.0, antenna_downtilt_deg=0.0,
    antenna_horizontal_pattern_path=None, antenna_vertical_pattern_path=None,
    clutter_enabled=False, clutter_grid=None, tx_clutter_override=None,
    rx_clutter_override=None, tx_clutter_loss_db=None, clutter_context=None,
    feedback=None, clutter_model: ClutterModel = "simple", cch_override_m=None,
    clutter_percentile=50.0, street_width_m=27.0,
    bel_enabled=False, bel_building_type: BuildingType = "traditional", bel_elevation_angle_deg=0.0,
):
    radius_m = radius_km * 1000.0
    min_lat, max_lat, min_lon, max_lon = coverage_bounds(tx_lat, tx_lon, radius_km)

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db
    lats = _coverage_axis_centers(min_lat, max_lat, grid_size)
    lons = _coverage_axis_centers(min_lon, max_lon, grid_size)

    antenna_config = antenna_config_from_values(
        preset=antenna_preset, azimuth_deg=antenna_az_deg,
        horizontal_beamwidth_deg=antenna_beamwidth_deg,
        front_back_db=antenna_front_back_db, downtilt_deg=antenna_downtilt_deg,
        horizontal_pattern_path=antenna_horizontal_pattern_path,
        vertical_pattern_path=antenna_vertical_pattern_path,
    )
    clutter_context = _build_clutter_context(
        clutter_enabled, clutter_context, f_mhz, tx_h_m, rx_h_m,
        cch_override_m, clutter_model,
        clutter_percentile, street_width_m, bel_enabled, bel_building_type,
        bel_elevation_angle_deg,
    )
    tx_clutter_loss = _compute_tx_clutter_loss(
        tx_lat, tx_lon, tx_clutter_loss_db, f_mhz,
        clutter_enabled, clutter_grid, tx_clutter_override,
        rx_clutter_override, clutter_context,
    )
    if clutter_enabled and clutter_model == "simple" and feedback:
        if clutter_percentile != 50.0:
            feedback.pushWarning(
                "CLUTTER_PERCENTILE=%.1f in simple mode only affects BEL; "
                "core clutter loss uses fixed category values. "
                "Use Advanced clutter model for full percentile modulation."
                % clutter_percentile)
    tasks = build_coverage_tasks(
        tx_lat, tx_lon, radius_m, grid_size, profile_step_m, max_profile_pts,
        tx_h_m, rx_h_m, climate, N0, f_mhz, polarization, epsilon, sigma,
        time_pct, location_pct, situation_pct, eirp_dbm, rx_gain_dbi,
        antenna_config, clutter_enabled, clutter_grid, tx_clutter_loss,
        rx_clutter_override, lats, lons, clutter_context=clutter_context,
        tx_clutter_override=tx_clutter_override,
    )
    if not tasks:
        logger.error("No coverage pixels within the specified radius.")
        if feedback:
            feedback.reportError(
                "No coverage pixels were generated within the specified radius. "
                "This may indicate the analysis area is too small or the TX "
                "coordinates are outside the DEM extent.", fatalError=False,
            )
        return None

    gs, nan32 = (grid_size, grid_size), np.float32(np.nan)
    prx_grid, loss_grid = np.full(gs, nan32, dtype=np.float32), np.full(gs, nan32, dtype=np.float32)
    itm_loss_grid = np.full(gs, nan32, dtype=np.float32)
    clutter_loss_grid, clutter_rx_db_grid = np.full(gs, nan32, dtype=np.float32), np.full(gs, nan32, dtype=np.float32)
    bel_rx_db_grid = np.full(gs, nan32, dtype=np.float32)
    grid_meta = elev_grid.grid_meta_dict()
    grid_meta["tx_lat"] = tx_lat
    grid_meta["tx_lon"] = tx_lon

    if feedback:
        feedback.pushInfo("Computing {} pixel tasks...".format(len(tasks)))

    grid_data = elev_grid.data
    logger.info(
        "Coverage grid: %dx%d, %d tasks, DEM shape=%s (%.1f MB)",
        grid_size, grid_size, len(tasks), grid_data.shape, grid_data.nbytes / BYTES_PER_MEBIBYTE,
    )

    cancelled, pixels_failed, pixels_done = execute_coverage_tasks(
        tasks, grid_data, grid_meta, feedback, loss_grid, prx_grid,
        itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid,
    )

    if cancelled:
        return None

    total = len(tasks)
    if feedback:
        feedback.pushInfo("Coverage: {}/{} pixels computed ({} failed)".format(
            total - pixels_failed, total, pixels_failed))

    log_coverage_failures(pixels_failed, total)

    return CoverageResult(
        prx_grid=prx_grid, loss_grid=loss_grid,
        min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon,
        itm_loss_grid=itm_loss_grid, clutter_loss_grid=clutter_loss_grid,
        clutter_rx_db_grid=clutter_rx_db_grid, bel_rx_db_grid=bel_rx_db_grid)
