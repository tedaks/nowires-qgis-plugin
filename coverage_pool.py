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
import multiprocessing.shared_memory
import os
import uuid
from collections import namedtuple
from typing import Optional

import numpy as np

from .antenna import antenna_gain_adjustment_db
from .coverage_compute import compute_itm_p2p
from .elevation import sample_line_from_grid

try:
    from concurrent.futures import BrokenExecutor as _BrokenPool
except ImportError:
    try:
        from concurrent.futures.process import BrokenProcessPool as _BrokenPool
    except ImportError:
        _BrokenPool = RuntimeError

logger = logging.getLogger(__name__)

_MAX_WORKERS = min(os.cpu_count() or 1, 16)
_MIN_CHUNK_SIZE = 64
_MAX_CHUNK_SIZE = 2048

_CoverageTask = namedtuple(
    "_CoverageTask",
    [
        "i", "j", "target_lat", "target_lon", "dist_m", "bearing",
        "step_m", "n_pts", "tx_h_m", "rx_h_m", "climate", "N0",
        "f_mhz", "polarization", "epsilon", "sigma",
        "time_pct", "location_pct", "situation_pct",
        "eirp_dbm", "antenna_config", "rx_gain_dbi",
        "clutter_tx_db", "clutter_rx_db",
    ],
)

_cov_shm: Optional[multiprocessing.shared_memory.SharedMemory] = None
_cov_grid_data: Optional[np.ndarray] = None
_cov_grid_meta: dict = {}


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
    _cov_shm = multiprocessing.shared_memory.SharedMemory(name=shm_name)
    _cov_grid_data = np.ndarray(shape, dtype=np.dtype(dtype_str), buffer=_cov_shm.buf)
    _cov_grid_meta = grid_meta



def _itm_worker(args, grid_data=None, grid_meta=None):
    task = _CoverageTask(*args)

    gd = grid_data if grid_data is not None else _cov_grid_data
    gm = grid_meta if grid_meta is not None else _cov_grid_meta

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
        logger.warning("Replacing %d NaN elevation value(s) with 0.0 (missing DEM data)", nan_count)
    elevs = np.where(np.isnan(elevs), 0.0, elevs)

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
    )


def _itm_worker_batch(batch_and_event):
    """Process a batch of coverage pixel tasks.

    *batch_and_event* is a tuple ``(batch, cancel_event)`` where
    *cancel_event* is a ``multiprocessing.Event`` (or None) used for
    early cancellation.
    """
    batch, cancel_event = batch_and_event
    results = []
    for args in batch:
        if cancel_event is not None and cancel_event.is_set():
            break
        try:
            results.append(_itm_worker(args))
        except Exception as exc:
            logger.warning("Coverage pixel task failed: %s", exc)
            results.append(None)
    return results


def _dynamic_chunk_size(n_tasks):
    """Choose chunk size based on task count: larger at start, smaller near end."""
    if n_tasks <= _MIN_CHUNK_SIZE:
        return _MIN_CHUNK_SIZE
    target_chunks = max(16, n_tasks // _MIN_CHUNK_SIZE)
    chunk = max(_MIN_CHUNK_SIZE, min(n_tasks // target_chunks, _MAX_CHUNK_SIZE))
    return chunk


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