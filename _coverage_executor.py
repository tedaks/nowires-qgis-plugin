# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import warnings
from concurrent.futures import ProcessPoolExecutor  # noqa: F401 re-exported for test mocking

import numpy as np

from .coverage_pool import (
    apply_batch_results,
    _dynamic_chunk_size,
    _init_cov_pool,
    _itm_worker,
    _itm_worker_batch,
    _make_shared_grid,
    _MAX_WORKERS,
    _release_shared_memory,
    should_use_multiprocessing,
)
from .macos_compat import configure_macos_multiprocessing, ensure_spawn_start_method

logger = logging.getLogger(__name__)


def _run_sequential(tasks, grid_data, grid_meta, feedback, prx_grid, loss_grid,
                    itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid):
    if feedback:
        feedback.pushInfo("Using single-threaded mode...")
    # 200 progress buckets for the whole run — finer than 100 without
    # adding measurable overhead.
    progress_interval = max(1, len(tasks) // 200)
    pixels_failed = 0
    pixels_done = 0
    cancelled = False
    for task_idx, task in enumerate(tasks):
        if feedback and feedback.isCanceled():
            cancelled = True
            break
        if not np.isnan(prx_grid[task.i, task.j]):
            pixels_done += 1
            continue
        result = _itm_worker(task, grid_data=grid_data, grid_meta=grid_meta)
        if result is not None:
            i, j, loss_db, prx, itm_loss_db, c_tx, c_rx, bel_rx = result
            loss_grid[i, j], prx_grid[i, j] = loss_db, prx
            itm_loss_grid[i, j] = itm_loss_db
            clutter_loss_grid[i, j] = c_tx + c_rx
            clutter_rx_db_grid[i, j], bel_rx_db_grid[i, j] = c_rx, bel_rx
        else:
            pixels_failed += 1
        pixels_done += 1
        if feedback and task_idx % progress_interval == 0:
            feedback.setProgress(int(pixels_done / max(len(tasks), 1) * 80))
    return cancelled, pixels_failed, pixels_done


def execute_coverage_tasks(
    tasks, grid_data, grid_meta, feedback, loss_grid, prx_grid,
    itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid,
):
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
            n_workers = max(1, min(os.cpu_count() or 1, _MAX_WORKERS))
            # No cancel_event between processes — earlier attempts (plain
            # multiprocessing.Event, then Manager().Event()) both failed on
            # macOS QGIS (the latter with EOFError when the Manager subprocess
            # died). Cancel responsiveness comes from breaking out of pool.map
            # between batches; in-flight batches finish (~64 tasks × ~5ms ≈
            # 320ms worst case at default chunk size).
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="resource_tracker", category=UserWarning)
                with ProcessPoolExecutor(
                    max_workers=n_workers,
                    initializer=_init_cov_pool,
                    initargs=(shared_grid.name, grid_data.shape, str(grid_data.dtype), grid_meta),
                ) as pool:
                    for chunk_idx, batch_results in enumerate(
                        pool.map(_itm_worker_batch, chunks, chunksize=1)
                    ):
                        if feedback and feedback.isCanceled():
                            cancelled = True
                            break
                        pixels_failed += apply_batch_results(
                            batch_results, loss_grid, prx_grid,
                            itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid,
                            bel_rx_db_grid)
                        pixels_done += len(batch_results)
                        if feedback and chunk_idx % 5 == 0:
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
        cancelled, pixels_failed, pixels_done = _run_sequential(
            tasks, grid_data, grid_meta, feedback, prx_grid, loss_grid,
            itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid)
    return cancelled, pixels_failed, pixels_done