# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
import logging
import math
import multiprocessing
import multiprocessing.shared_memory
import os
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional

import numpy as np

from NoWires.antenna import antenna_gain_adjustment_db
from NoWires.coverage.compute import compute_itm_p2p
from NoWires.coverage._result_dispatch import WorkerError, apply_batch_results, log_coverage_failures
from NoWires._geo_utils import sample_line_from_grid
from NoWires.macos_compat import find_macos_python_executable
from NoWires.shared_dem_grid import SharedDEMGrid

logger = logging.getLogger(__name__)

def _get_max_workers():
    """Return the maximum number of worker processes (lazy env-var lookup)."""
    return min(os.cpu_count() or 1, int(os.environ.get("NOWIRES_MAX_WORKERS", "16")))

_MAX_WORKERS = _get_max_workers()
_MIN_CHUNK_SIZE = 64
_MAX_CHUNK_SIZE = 2048

def _interpolate_nan_elevations(elevs):
    """Replace NaN elevation values with linearly interpolated neighbours."""
    from NoWires.nan_utils import interpolate_nan_array
    return interpolate_nan_array(elevs)

@dataclass
class CoverageResult:
    prx_grid: np.ndarray
    loss_grid: np.ndarray
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    itm_loss_grid: np.ndarray
    clutter_loss_grid: np.ndarray
    clutter_rx_db_grid: np.ndarray
    bel_rx_db_grid: np.ndarray

_CoverageTask = namedtuple(
    "_CoverageTask",
    [
        "i", "j", "target_lat", "target_lon", "dist_m", "bearing",
        "step_m", "n_pts", "tx_h_m", "rx_h_m", "climate", "N0",
        "f_mhz", "polarization", "epsilon", "sigma",
        "time_pct", "location_pct", "situation_pct",
        "eirp_dbm", "antenna_config", "rx_gain_dbi",
        "clutter_tx_db", "clutter_rx_db", "bel_rx_db",
    ],
)

# Module-level shared-memory state for worker processes.
# Set per-pool by _init_cov_pool, read by _itm_worker. Safe under spawn
# (each worker gets its own copy). NoThreading flag prevents concurrent
# runs in the same process.
_cov_shm: Optional[multiprocessing.shared_memory.SharedMemory] = None
_cov_grid_data: Optional[np.ndarray] = None
_cov_grid_meta: dict = {}
_cov_pool_atexit_registered: bool = False


def should_use_multiprocessing(os_name=None, platform_name=None):
    """Return whether process-based parallelism is safe in this runtime.

    On macOS and Windows the platform-specific ``find_*_python_executable``
    helpers validate each candidate; a False return here triggers the
    clean sequential fallback in the executor.
    """
    import sys
    if os_name is None:
        os_name = os.name
    if platform_name is None:
        platform_name = sys.platform
    if os_name == "nt":
        from NoWires.windows_compat import find_windows_python_executable
        if find_windows_python_executable() is None:
            logger.warning("Windows: no usable Python for multiprocessing; "
                           "falling back to sequential mode.")
            return False
    if platform_name == "darwin" and find_macos_python_executable() is None:
        logger.warning("macOS: no usable Python for multiprocessing; "
                       "falling back to sequential mode.")
        return False
    return True


def _ensure_path():
    """Ensure the plugin and its parent directory are on sys.path.

    On Windows (spawn start method), child processes do not inherit
    QGIS's dynamically-added sys.path entries. Without the plugin's
    parent directory on sys.path, relative imports like
    ``from .antenna import ...`` fail in worker processes.
    """
    import sys

    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugins_dir = os.path.dirname(plugin_dir)
    if plugins_dir not in sys.path:
        sys.path.insert(0, plugins_dir)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def _final_cov_pool():
    """Finalizer: close the per-worker shared-memory handle on pool shutdown."""
    global _cov_shm, _cov_grid_data, _cov_grid_meta
    if _cov_grid_data is not None:
        _cov_grid_data = None
    if _cov_shm is not None:
        try:
            _cov_shm.close()
        except Exception:
            pass
        _cov_shm = None


def _init_cov_pool(shm_name, shape, dtype_str, grid_meta):
    _ensure_path()
    global _cov_shm, _cov_grid_data, _cov_grid_meta
    # Reset stale state when a worker is reused across runs (rare under
    # ProcessPoolExecutor; possible when threading is enabled). Previously
    # this branch raised RuntimeError — friendlier to just rebind.
    if _cov_grid_data is not None:
        _cov_grid_data = None
    if _cov_shm is not None:
        try:
            _cov_shm.close()
        except Exception:
            pass
        _cov_shm = None
    _cov_shm = multiprocessing.shared_memory.SharedMemory(name=shm_name)
    _cov_grid_data = np.ndarray(shape, dtype=np.dtype(dtype_str), buffer=_cov_shm.buf)
    _cov_grid_meta = grid_meta
    global _cov_pool_atexit_registered
    if not _cov_pool_atexit_registered:
        atexit.register(_final_cov_pool)
        _cov_pool_atexit_registered = True


def _itm_worker(args, grid_data=None, grid_meta=None):
    task = _CoverageTask(*args)

    gd = grid_data if grid_data is not None else _cov_grid_data
    gm = grid_meta if grid_meta is not None else _cov_grid_meta
    if gd is None:
        raise RuntimeError("No DEM grid data available for coverage worker")
    if not gm:
        raise RuntimeError("No DEM grid metadata available for coverage worker")

    elevs = sample_line_from_grid(
        gd,
        gm,
        gm["tx_lat"],
        gm["tx_lon"],
        task.target_lat,
        task.target_lon,
        task.n_pts,
    )
    if np.all(np.isnan(elevs)):
        return None
    nan_count = int(np.isnan(elevs).sum())
    if nan_count > 0:
        logger.warning(
            "Interpolating %d NaN elevation value(s) from nearest valid "
            "samples (missing DEM data)",
            nan_count,
        )
    elevs = _interpolate_nan_elevations(elevs)

    vertical_angle_deg = math.degrees(
        math.atan2(
            (float(elevs[-1]) + task.rx_h_m) - (float(elevs[0]) + task.tx_h_m),
            max(task.dist_m, 1.0),
        )
    )
    ant_gain_adj = antenna_gain_adjustment_db(
        bearing_deg=task.bearing,
        elevation_angle_deg=vertical_angle_deg,
        config=task.antenna_config,
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
        ant_gain_adj=ant_gain_adj,
        rx_gain_dbi=task.rx_gain_dbi,
        clutter_tx_db=task.clutter_tx_db,
        clutter_rx_db=task.clutter_rx_db,
        bel_rx_db=task.bel_rx_db,
    )

    if result is None:
        return None

    return (
        task.i,
        task.j,
        result["total_path_loss_db"],
        result["received_power_dbm"],
        result["itm_loss_db"],
        result["clutter_tx_db"],
        result["clutter_rx_db"],
        result["bel_rx_db"],
    )


def _itm_worker_batch(batch):
    """Process a batch of coverage pixel tasks.

    No cross-process cancel signal — earlier attempts to share one via
    multiprocessing.Event() / Manager().Event() failed on macOS QGIS.
    Cancel responsiveness comes from breaking out of ``pool.map`` between
    batches in the executor (~320 ms worst-case wait at default chunk size).
    """
    results = []
    for args in batch:
        try:
            results.append(_itm_worker(args))
        except Exception as exc:
            results.append(WorkerError("{}: {}".format(type(exc).__name__, exc)))
    return results


def _dynamic_chunk_size(n_tasks):
    """Choose chunk size based on task count.

    Aims for at least target_chunks chunks (≥16) so that progress
    reporting updates frequently enough.  Each chunk contains
    chunk tasks, clamped to [_MIN_CHUNK_SIZE, _MAX_CHUNK_SIZE].
    For example, with 1024 tasks the target is 16 chunks of 64 tasks each.
    """
    if n_tasks <= _MIN_CHUNK_SIZE:
        return _MIN_CHUNK_SIZE
    target_chunks = max(16, n_tasks // _MIN_CHUNK_SIZE)
    chunk = max(_MIN_CHUNK_SIZE, min(n_tasks // target_chunks, _MAX_CHUNK_SIZE))
    return chunk


def _make_shared_grid(grid_data):
    return SharedDEMGrid(grid_data)


def _release_shared_memory(shared_grid, unlink=True):
    if shared_grid is None:
        return
    shared_grid.release()


__all__ = [
    "CoverageResult",
    "apply_batch_results",
    "log_coverage_failures",
    "should_use_multiprocessing",
]
