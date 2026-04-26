# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2024 Bortre Tenamo
                               Adaptations (C) 2026 by Bortre Tenamo
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

# Coverage computation engine for area prediction and radius sweep.
#
# Computes per-pixel ITM predictions using multiprocessing, producing
# received power (dBm) grids for visualization as QGIS raster layers.
#
# Uses shared memory to avoid OOM when distributing the DEM grid to workers.
#
# Portions of this module are adapted from the tedaks/nowires web application
# and were originally distributed under the MIT License. See NOTICE.md for
# attribution details.

import logging
import math
import multiprocessing
import multiprocessing.shared_memory
import os
import uuid
from concurrent.futures import ProcessPoolExecutor

try:
    from concurrent.futures import BrokenExecutor as _BrokenPool
except ImportError:
    try:
        from concurrent.futures.process import BrokenProcessPool as _BrokenPool
    except ImportError:
        _BrokenPool = RuntimeError
from typing import Optional

from .coverage_compute import compute_itm_p2p

import numpy as np

from .antenna import antenna_gain_factor
from .elevation import sample_line_from_grid

logger = logging.getLogger(__name__)

ITM_LOSS_UPPER_BOUND = 400.0
RADIUS_CONSECUTIVE_MISS_LIMIT = 3
_MAX_WORKERS = os.cpu_count() or 1
_MIN_CHUNK_SIZE = 64
_MAX_CHUNK_SIZE = 2048
_MIN_COVERAGE_DISTANCE_M = 1.0
METERS_PER_DEGREE_LAT = 111320.0

from collections import namedtuple

_CoverageTask = namedtuple(
    "_CoverageTask",
    [
        "i", "j", "target_lat", "target_lon", "dist_m", "bearing",
        "step_m", "n_pts", "tx_h_m", "rx_h_m", "climate", "N0",
        "f_mhz", "polarization", "epsilon", "sigma",
        "time_pct", "location_pct", "situation_pct",
        "eirp_dbm", "ant_gain_adj", "rx_gain_dbi",
    ],
)

_cov_shm: Optional[multiprocessing.shared_memory.SharedMemory] = None
_cov_grid_data: Optional[np.ndarray] = None
_cov_grid_meta: dict = {}
_itm_imports = None

def should_use_multiprocessing(os_name=None):
    """Return whether process-based parallelism is safe in this runtime."""
    if os_name is None:
        os_name = os.name
    return os_name != "nt"


def _ensure_path():
    """Ensure the plugin and its parent directory are on sys.path.

    On Windows (spawn start method), child processes do not inherit
    QGIS's dynamically-added sys.path entries. Without the plugin's
    parent directory on sys.path, relative imports like
    ``from .antenna import ...`` fail in worker processes.
    """
    import sys

    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    plugins_dir = os.path.dirname(plugin_dir)
    if plugins_dir not in sys.path:
        sys.path.insert(0, plugins_dir)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def _init_cov_pool(shm_name, shape, dtype_str, grid_meta):
    _ensure_path()
    global _cov_shm, _cov_grid_data, _cov_grid_meta
    _cov_shm = multiprocessing.shared_memory.SharedMemory(name=shm_name)
    _cov_grid_data = np.ndarray(shape, dtype=np.dtype(dtype_str), buffer=_cov_shm.buf)
    _cov_grid_meta = grid_meta


def _cleanup_cov_pool():
    global _cov_shm, _cov_grid_data
    if _cov_grid_data is not None:
        _cov_grid_data = None
    if _cov_shm is not None:
        _cov_shm.close()
        _cov_shm = None


def _itm_worker(args):
    task = _CoverageTask(*args)

    elevs = sample_line_from_grid(
        _cov_grid_data,
        _cov_grid_meta,
        _cov_grid_meta["tx_lat"],
        _cov_grid_meta["tx_lon"],
        task.target_lat,
        task.target_lon,
        task.n_pts,
    )

    result = compute_itm_p2p(
        h_tx__meter=task.tx_h_m,
        h_rx__meter=task.rx_h_m,
        elevations=elevs,
        resolution=task.step_m,
        climate_idx=int(task.climate),
        N_0=task.N0,
        f__mhz=task.f_mhz,
        polarization=int(task.polarization),
        epsilon=task.epsilon,
        sigma=task.sigma,
        time_pct=task.time_pct,
        location_pct=task.location_pct,
        situation_pct=task.situation_pct,
        eirp_dbm=task.eirp_dbm,
        ant_gain_adj=task.ant_gain_adj,
        rx_gain_dbi=task.rx_gain_dbi,
    )

    if result is None:
        return None

    loss_db, prx = result
    return (task.i, task.j, loss_db, prx)


def _itm_worker_batch(batch):
    results = []
    # Cancellation is checked between chunks at the caller level;
    # per-task cancellation inside workers is not possible because
    # we cannot propagate feedback signals into the worker process.
    for args in batch:
        results.append(_itm_worker(args))
    return results


def _dynamic_chunk_size(n_tasks):
    """Choose chunk size based on task count: larger at start, smaller near end."""
    if n_tasks <= _MIN_CHUNK_SIZE:
        return _MIN_CHUNK_SIZE
    target_chunks = max(16, n_tasks // _MIN_CHUNK_SIZE)
    chunk = max(_MIN_CHUNK_SIZE, min(n_tasks // target_chunks, _MAX_CHUNK_SIZE))
    return chunk


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
    antenna_az_deg,
    antenna_beamwidth_deg,
    lats,
    lons,
):
    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    dlat = (lats[:, np.newaxis] - tx_lat) / lat_per_m
    dlon = (lons[np.newaxis, :] - tx_lon) / lon_per_m
    dist_grid = np.sqrt(dlat * dlat + dlon * dlon)
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
            ant_gain = antenna_gain_factor(b, antenna_az_deg, antenna_beamwidth_deg)
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
                    ant_gain,
                    rx_gain_dbi,
                )
            )
    return tasks


def _make_shared_grid(grid_data):
    name = uuid.uuid4().hex[:20]
    shm = multiprocessing.shared_memory.SharedMemory(
        create=True,
        name=name,
        size=grid_data.nbytes,
    )
    try:
        shared_arr = np.ndarray(grid_data.shape, dtype=grid_data.dtype, buffer=shm.buf)
        shared_arr[:] = grid_data[:]
    except Exception:
        try:
            shm.unlink()
        except Exception:
            pass
        raise
    return shm


def _release_shared_memory(shm):
    if shm is None:
        return
    try:
        shm.close()
    except Exception:
        pass
    try:
        shm.unlink()
    except Exception:
        pass


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
    feedback=None,
):
    global _cov_grid_data, _cov_grid_meta
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
        antenna_az_deg,
        antenna_beamwidth_deg,
        lats,
        lons,
    )

    if not tasks:
        logger.warning("No coverage pixels within the specified radius.")
        return prx_grid, loss_grid, min_lat, max_lat, min_lon, max_lon

    grid_meta = elev_grid.grid_meta_dict()
    grid_meta["tx_lat"] = tx_lat
    grid_meta["tx_lon"] = tx_lon

    if feedback:
        feedback.pushInfo("Computing {} pixel tasks...".format(len(tasks)))

    grid_data = elev_grid.data
    logger.info(
        "Coverage grid: %dx%d, %d tasks, DEM shape=%s (%.1f MB)",
        grid_size,
        grid_size,
        len(tasks),
        grid_data.shape,
        grid_data.nbytes / 1048576.0,
    )

    shm = None
    n_workers = _MAX_WORKERS
    pixels_failed = 0
    pixels_done = 0

    chunk_size = _dynamic_chunk_size(len(tasks))
    chunks = [tasks[i : i + chunk_size] for i in range(0, len(tasks), chunk_size)]

    use_multiprocessing = should_use_multiprocessing()
    if use_multiprocessing:
        if feedback:
            feedback.pushInfo(
                "Computing {} pixels with {} workers...".format(len(tasks), n_workers)
            )
        try:
            shm = _make_shared_grid(grid_data)
            with ProcessPoolExecutor(
                max_workers=n_workers,
                initializer=_init_cov_pool,
                initargs=(shm.name, grid_data.shape, str(grid_data.dtype), grid_meta),
            ) as pool:
                for chunk_idx, batch_results in enumerate(
                    pool.map(_itm_worker_batch, chunks, chunksize=1)
                ):
                    if feedback and feedback.isCanceled():
                        logger.info("Coverage cancelled by user")
                        _release_shared_memory(shm)
                        return None, None, 0, 0, 0, 0
                    for result in batch_results:
                        if result is not None:
                            i, j, loss_db, prx = result
                            loss_grid[i, j] = loss_db
                            prx_grid[i, j] = prx
                        else:
                            pixels_failed += 1
                        pixels_done += 1
                    if feedback and chunk_idx % 50 == 0:
                        pct = int(pixels_done / len(tasks) * 80)
                        feedback.setProgress(pct)
        except (_BrokenPool, ImportError, OSError, RuntimeError) as exc:
            logger.warning(
                "Multiprocessing failed (%s: %s), falling back to sequential",
                type(exc).__name__,
                exc,
            )
            if feedback:
                feedback.pushInfo(
                    "Multiprocessing unavailable, using single-threaded mode..."
                )
            use_multiprocessing = False
    elif feedback:
        feedback.pushInfo(
            "Using single-threaded mode on Windows (multiprocessing unsafe)..."
        )

    # Sequential fallback
    if not use_multiprocessing:
        _cov_grid_data = grid_data
        _cov_grid_meta = grid_meta

        for task_idx, task in enumerate(tasks):
            if feedback and feedback.isCanceled():
                logger.info("Coverage cancelled by user")
                return None, None, 0, 0, 0, 0
            result = _itm_worker(task)
            if result is not None:
                i, j, loss_db, prx = result
                loss_grid[i, j] = loss_db
                prx_grid[i, j] = prx
            else:
                pixels_failed += 1
            pixels_done += 1
            if feedback and task_idx % 500 == 0:
                pct = int(pixels_done / len(tasks) * 80)
                feedback.setProgress(pct)

        # Clear globals after sequential run
        _cov_grid_data = None
        _cov_grid_meta = {}

    # Always clean up shared memory
    _release_shared_memory(shm)

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
        logger.warning(
            "Coverage: %d/%d pixels failed (%.1f%%)",
            pixels_failed,
            total,
            failure_pct,
        )

    return prx_grid, loss_grid, min_lat, max_lat, min_lon, max_lon
