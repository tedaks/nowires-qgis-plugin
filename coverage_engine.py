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
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .antenna import antenna_config_from_values
from .coverage_pool import (
    _dynamic_chunk_size,
    _init_cov_pool,
    _itm_worker,
    _itm_worker_batch,
    _make_shared_grid,
    _MAX_WORKERS,
    _release_shared_memory,
    should_use_multiprocessing,
)
from .constants import BYTES_PER_MEBIBYTE
from .coverage_tasks import (
    METERS_PER_DEGREE_LAT,
    _coverage_axis_centers,
    build_coverage_tasks,
)

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
    feedback=None,
):
    from .clutter import compute_terminal_clutter_losses
    from . import coverage_pool

    radius_m = radius_km * 1000.0
    lat_per_m = 1.0 / METERS_PER_DEGREE_LAT
    lon_per_m = 1.0 / (METERS_PER_DEGREE_LAT * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = radius_m * lat_per_m
    half_lon = radius_m * lon_per_m
    min_lat = tx_lat - half_lat
    max_lat = tx_lat + half_lat
    min_lon = tx_lon - half_lon
    max_lon = tx_lon + half_lon

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db
    lats = _coverage_axis_centers(min_lat, max_lat, grid_size)
    lons = _coverage_axis_centers(min_lon, max_lon, grid_size)
    prx_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    itm_loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    clutter_loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)

    antenna_config = antenna_config_from_values(
        preset=antenna_preset,
        azimuth_deg=antenna_az_deg,
        horizontal_beamwidth_deg=antenna_beamwidth_deg,
        front_back_db=antenna_front_back_db,
        downtilt_deg=antenna_downtilt_deg,
        horizontal_pattern_path=antenna_horizontal_pattern_path,
        vertical_pattern_path=antenna_vertical_pattern_path,
    )

    tx_clutter = compute_terminal_clutter_losses(
        tx_lat=tx_lat,
        tx_lon=tx_lon,
        rx_lat=tx_lat,
        rx_lon=tx_lon,
        frequency_mhz=f_mhz,
        enabled=clutter_enabled,
        land_cover_grid=clutter_grid,
        tx_override=tx_clutter_override,
        rx_override=rx_clutter_override,
    )

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
        tx_clutter.tx_loss_db,
        rx_clutter_override,
        lats,
        lons,
    )

    if not tasks:
        logger.warning("No coverage pixels within the specified radius.")
        return (
            prx_grid, loss_grid, min_lat, max_lat,
            min_lon, max_lon, itm_loss_grid, clutter_loss_grid,
        )

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

    shm = None
    n_workers = max(1, min(os.cpu_count() or 1, _MAX_WORKERS))
    pixels_failed = 0
    pixels_done = 0

    chunk_size = _dynamic_chunk_size(len(tasks))
    chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]

    cancelled = False
    use_mp = should_use_multiprocessing()
    if use_mp:
        if feedback:
            feedback.pushInfo(
                "Computing {} pixels with {} workers...".format(len(tasks), n_workers)
            )
        try:
            try:
                shm = _make_shared_grid(grid_data)
                cancel_event = multiprocessing.Event()
                with ProcessPoolExecutor(
                    max_workers=n_workers,
                    initializer=_init_cov_pool,
                    initargs=(shm.name, grid_data.shape, str(grid_data.dtype), grid_meta),
                ) as pool:
                    for chunk_idx, batch_results in enumerate(
                        pool.map(
                            _itm_worker_batch,
                            [(c, cancel_event) for c in chunks],
                            chunksize=1,
                        )
                    ):
                        if feedback and feedback.isCanceled():
                            logger.info("Coverage cancelled by user")
                            cancelled = True
                            cancel_event.set()
                            break
                        for result in batch_results:
                            if result is not None:
                                i, j, loss_db, prx, itm_loss_db, c_tx, c_rx = result
                                loss_grid[i, j] = loss_db
                                prx_grid[i, j] = prx
                                itm_loss_grid[i, j] = itm_loss_db
                                clutter_loss_grid[i, j] = c_tx + c_rx
                            else:
                                pixels_failed += 1
                            pixels_done += 1
                        if feedback and chunk_idx % 50 == 0:
                            pct = int(pixels_done / len(tasks) * 80)
                            feedback.setProgress(pct)
            except Exception as exc:
                logger.warning(
                    "Multiprocessing failed (%s: %s), falling back to sequential",
                    type(exc).__name__,
                    exc,
                )
                if feedback:
                    feedback.pushInfo(
                        "Multiprocessing unavailable, using single-threaded mode..."
                    )
                use_mp = False
        finally:
            _release_shared_memory(shm)
            shm = None
    elif feedback:
        feedback.pushInfo(
            "Using single-threaded mode on Windows (multiprocessing unsafe)..."
        )

    if not use_mp:
        try:
            for task_idx, task in enumerate(tasks):
                if feedback and feedback.isCanceled():
                    logger.info("Coverage cancelled by user")
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
                    pct = int(pixels_done / len(tasks) * 80)
                    feedback.setProgress(pct)
        finally:
            coverage_pool._cov_grid_data = None
            coverage_pool._cov_grid_meta = {}

    if cancelled:
        return None, None, 0.0, 0.0, 0.0, 0.0, None, None

    total = len(tasks)
    if feedback:
        feedback.pushInfo(
            "Coverage: {}/{} pixels computed ({} failed)".format(
                total - pixels_failed, total, pixels_failed
            )
        )

    failure_pct = pixels_failed / max(total, 1) * 100
    if failure_pct > 50:
        logger.error("High failure rate: %.1f%% of coverage pixels failed", failure_pct)
    elif pixels_failed > 0:
        logger.warning("Coverage: %d/%d pixels failed (%.1f%%)", pixels_failed, total, failure_pct)

    return (
        prx_grid, loss_grid, min_lat, max_lat,
        min_lon, max_lon, itm_loss_grid, clutter_loss_grid,
    )