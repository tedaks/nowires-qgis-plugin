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

import logging
import math
import multiprocessing
import os
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .antenna import antenna_config_from_values
from .clutter import compute_terminal_clutter_losses
from .clutter_context import ClutterLossContext
from .coverage_pool import (
    apply_batch_results,
    CoverageResult,
    _dynamic_chunk_size,
    _init_cov_pool,
    _itm_worker,
    _itm_worker_batch,
    log_coverage_failures,
    _make_shared_grid,
    _MAX_WORKERS,
    _release_shared_memory,
    should_use_multiprocessing,
)
from .macos_compat import configure_macos_multiprocessing, ensure_spawn_start_method
from .constants import BYTES_PER_MEBIBYTE
from .coverage_tasks import (
    _coverage_axis_centers,
    build_coverage_tasks,
)
from .geo_bounds import coverage_bounds

logger = logging.getLogger(__name__)



def compute_coverage(
    elev_grid,
    tx_lat,
    tx_lon,
    tx_h_m,
    rx_h_m,
    f_mhz,
    grid_size=192,
    radius_km=50.0,
    profile_step_m=250.0,
    max_profile_pts=75,
    tx_power_dbm=43.0,
    tx_gain_dbi=8.0,
    rx_gain_dbi=2.0,
    cable_loss_db=2.0,
    rx_sensitivity_dbm=-100.0,
    antenna_az_deg=None,
    antenna_beamwidth_deg=360.0,
    polarization=0,
    climate=1,
    N0=301.0,
    epsilon=15.0,
    sigma=0.005,
    time_pct=50.0,
    location_pct=50.0,
    situation_pct=50.0,
    antenna_preset=0,
    antenna_front_back_db=25.0,
    antenna_downtilt_deg=0.0,
    antenna_horizontal_pattern_path=None,
    antenna_vertical_pattern_path=None,
    clutter_enabled=False,
    clutter_grid=None,
    tx_clutter_override=None,
    rx_clutter_override=None,
    tx_clutter_loss_db=None,
    feedback=None,
    clutter_model="simple",
    cch_override_m=None,
    clutter_percentile=50.0, street_width_m=27.0,
    bel_enabled=False, bel_building_type="traditional", bel_elevation_angle_deg=0.0,
):
    radius_m = radius_km * 1000.0
    min_lat, max_lat, min_lon, max_lon = coverage_bounds(tx_lat, tx_lon, radius_km)

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db
    lats = _coverage_axis_centers(min_lat, max_lat, grid_size)
    lons = _coverage_axis_centers(min_lon, max_lon, grid_size)
    prx_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    itm_loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    clutter_loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)

    _sample_elev = getattr(elev_grid, "sample", None)
    if callable(_sample_elev):
        tx_ground_elev_m = float(_sample_elev(tx_lat, tx_lon))
        if not math.isfinite(tx_ground_elev_m):
            tx_ground_elev_m = 0.0
    else:
        tx_ground_elev_m = 0.0
    rx_ground_grid = None
    if clutter_enabled and clutter_model == "advanced" and callable(_sample_elev):
        rx_ground_grid = np.zeros((grid_size, grid_size), dtype=np.float32)
        for i in range(grid_size):
            lat_i = float(lats[i])
            for j in range(grid_size):
                v = _sample_elev(lat_i, float(lons[j]))
                rx_ground_grid[i, j] = v if math.isfinite(v) else 0.0

    antenna_config = antenna_config_from_values(
        preset=antenna_preset,
        azimuth_deg=antenna_az_deg,
        horizontal_beamwidth_deg=antenna_beamwidth_deg,
        front_back_db=antenna_front_back_db,
        downtilt_deg=antenna_downtilt_deg,
        horizontal_pattern_path=antenna_horizontal_pattern_path,
        vertical_pattern_path=antenna_vertical_pattern_path,
    )
    clutter_context = None
    if clutter_enabled:
        clutter_context = ClutterLossContext(
            frequency_mhz=f_mhz, distance_m=0.0,
            tx_height_m=tx_h_m, rx_height_m=rx_h_m,
            rx_ground_elevation_m=tx_ground_elev_m,
            tx_ground_elevation_m=tx_ground_elev_m,
            polarization=polarization,
            cch_override_m=cch_override_m, model=clutter_model,
            percentile=clutter_percentile, street_width_m=street_width_m,
            bel_enabled=bel_enabled, bel_building_type=bel_building_type,
            bel_elevation_angle_deg=bel_elevation_angle_deg,
        )
    if tx_clutter_loss_db is not None:
        tx_clutter_loss = tx_clutter_loss_db
    else:
        tx_clutter = compute_terminal_clutter_losses(
            tx_lat=tx_lat, tx_lon=tx_lon,
            rx_lat=tx_lat, rx_lon=tx_lon,
            frequency_mhz=f_mhz, enabled=clutter_enabled,
            land_cover_grid=clutter_grid,
            tx_override=tx_clutter_override,
            rx_override=rx_clutter_override,
            context=clutter_context,
        )
        tx_clutter_loss = tx_clutter.tx_loss_db
    tasks = build_coverage_tasks(
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
        tx_clutter_loss,
        rx_clutter_override,
        lats, lons, clutter_context=clutter_context,
        tx_clutter_override=tx_clutter_override,
        tx_ground_elev_m=tx_ground_elev_m,
        rx_ground_grid=rx_ground_grid,
    )
    if not tasks:
        logger.error("No coverage pixels within the specified radius.")
        return None
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

    chunk_size = _dynamic_chunk_size(len(tasks))
    chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
    cancelled = False
    use_mp = should_use_multiprocessing()
    pixels_failed = 0
    pixels_done = 0
    if use_mp:
        ensure_spawn_start_method()
        configure_macos_multiprocessing()
        if feedback:
            feedback.pushInfo(
                "Computing {} pixels with {} workers...".format(
                    len(tasks), max(1, min(os.cpu_count() or 1, _MAX_WORKERS)))
            )
        shared_grid = None
        try:
            shared_grid = _make_shared_grid(grid_data)
            cancel_event = multiprocessing.Event()
            n_workers = max(1, min(os.cpu_count() or 1, _MAX_WORKERS))
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="resource_tracker", category=UserWarning)
                with ProcessPoolExecutor(
                    max_workers=n_workers,
                    initializer=_init_cov_pool,
                    initargs=(shared_grid.name, grid_data.shape, str(grid_data.dtype), grid_meta),
                ) as pool:
                    for chunk_idx, batch_results in enumerate(
                        pool.map(
                            _itm_worker_batch,
                            [(c, cancel_event) for c in chunks],
                            chunksize=1,
                        )
                    ):
                        if feedback and feedback.isCanceled():
                            cancelled = True
                            cancel_event.set()
                            break
                        pixels_failed += apply_batch_results(
                            batch_results, loss_grid, prx_grid, itm_loss_grid, clutter_loss_grid)
                        pixels_done += len(batch_results)
                        if feedback and chunk_idx % 50 == 0:
                            feedback.setProgress(int(pixels_done / len(tasks) * 80))
        except Exception as exc:
            logger.warning(
                "Multiprocessing failed (%s: %s), falling back to sequential",
                type(exc).__name__, exc,
            )
            use_mp = False
            if feedback:
                feedback.pushInfo("Multiprocessing unavailable, using single-threaded mode...")
        finally:
            if shared_grid is not None:
                _release_shared_memory(shared_grid)
    if not use_mp:
        if feedback:
            feedback.pushInfo("Using single-threaded mode...")
        for task_idx, task in enumerate(tasks):
            if feedback and feedback.isCanceled():
                cancelled = True
                break
            result = _itm_worker(task, grid_data=grid_data, grid_meta=grid_meta)
            if result is not None:
                i, j, loss_db, prx, itm_loss_db, c_tx, c_rx = result
                loss_grid[i, j] = loss_db
                prx_grid[i, j] = prx
                itm_loss_grid[i, j] = itm_loss_db
                clutter_loss_grid[i, j] = c_tx + c_rx
            else:
                pixels_failed += 1
            pixels_done += 1
            if feedback and task_idx % 500 == 0:
                feedback.setProgress(int(pixels_done / max(len(tasks), 1) * 80))

    if cancelled:
        return CoverageResult(
            prx_grid=None, loss_grid=None, min_lat=0.0, max_lat=0.0,
            min_lon=0.0, max_lon=0.0, itm_loss_grid=None, clutter_loss_grid=None)

    total = len(tasks)
    if feedback:
        feedback.pushInfo("Coverage: {}/{} pixels computed ({} failed)".format(
            total - pixels_failed, total, pixels_failed))

    log_coverage_failures(pixels_failed, total)

    return CoverageResult(
        prx_grid=prx_grid, loss_grid=loss_grid,
        min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon,
        itm_loss_grid=itm_loss_grid, clutter_loss_grid=clutter_loss_grid)
