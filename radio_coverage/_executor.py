# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

import logging
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor  # noqa: F401 re-exported for test mocking

import numpy as np

from NoWires.radio_coverage.pool import (
    apply_batch_results,
    _dynamic_chunk_size,
    _itm_worker,
    _make_shared_grid,
    _MAX_WORKERS,
    _release_shared_memory,
    should_use_multiprocessing,
)
from NoWires.macos_compat import configure_macos_multiprocessing, ensure_spawn_start_method
from NoWires.windows_compat import configure_windows_multiprocessing

logger = logging.getLogger(__name__)


def _run_sequential(tasks, grid_data, grid_meta, feedback, prx_grid, loss_grid,
                    itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid):
    if feedback:
        feedback.pushInfo("Single-threaded mode: no multiprocessing detected")
    start_time = time.time()
    total = len(tasks)
    progress_interval = max(1, total // 200)
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
            progress = pixels_done / max(total, 1)
            elapsed = time.time() - start_time
            rate = pixels_done / elapsed if elapsed > 0 else 0
            eta = (total - pixels_done) / rate if rate > 0 else 0
            feedback.setProgress(int(progress * 80))
            feedback.pushInfo(
                "{:.0f}% · {:.0f} pix/s · ETA {:.0f}s ({}/{})".format(
                    progress * 100, rate, eta, pixels_done, total))
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
    start_time = time.time()
    total = len(tasks)
    if use_mp:
        ensure_spawn_start_method()
        configure_macos_multiprocessing()
        configure_windows_multiprocessing()
        if feedback:
            feedback.pushInfo(
                "Computing {} pixels with {} workers...".format(
                    len(tasks), max(1, min(os.cpu_count() or 1, _MAX_WORKERS)))
            )
        # Resolve _init_cov_pool / _itm_worker_batch through the import
        # machinery at call time rather than holding references frozen at
        # module-import time. pickle's identity check
        # (`getattr(sys.modules[fn.__module__], fn.__qualname__) is fn`)
        # fails if radio_coverage_pool is re-imported under the same name after
        # _coverage_executor was loaded — e.g., during a QGIS plugin reload
        # that touches only some plugin modules. A function-local
        # `from .radio_coverage_pool import ...` re-binds these names against
        # the current sys.modules entry each call, so the references handed
        # to ProcessPoolExecutor are exactly the ones pickle finds.
        from NoWires.radio_coverage.pool import _init_cov_pool, _itm_worker_batch
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
                            progress = pixels_done / total
                            elapsed = time.time() - start_time
                            rate = pixels_done / elapsed if elapsed > 0 else 0
                            eta = (total - pixels_done) / rate if rate > 0 else 0
                            feedback.setProgress(int(progress * 80))
                            feedback.pushInfo(
                                "{:.0f}% · {:.0f} pix/s · ETA {:.0f}s ({}/{})".format(
                                    progress * 100, rate, eta, pixels_done, total))
        except Exception as exc:
            logger.warning(
                "Multiprocessing failed (%s: %s), falling back to sequential",
                type(exc).__name__, exc,
            )
            use_mp = False
            # Route the exception details through feedback.pushWarning so the
            # cause is visible in the QGIS Processing log panel. Python
            # logger.warning above can land on a StreamHandler with stream=None
            # in a GUI-subsystem QGIS build (pythonw.exe-style) and silently
            # drop the message — leaving the user staring at an opaque
            # "Multiprocessing unavailable" with no diagnostic trail.
            if feedback:
                feedback.pushWarning(
                    "Multiprocessing unavailable ({}: {}), using single-threaded mode...".format(
                        type(exc).__name__, exc,
                    )
                )
        finally:
            if shared_grid is not None:
                _release_shared_memory(shared_grid)
    if not use_mp:
        seq_cancelled, seq_failed, seq_done = _run_sequential(
            tasks, grid_data, grid_meta, feedback, prx_grid, loss_grid,
            itm_loss_grid, clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid)
        pixels_failed = seq_failed
        pixels_done = seq_done
        cancelled = cancelled or seq_cancelled
    return cancelled, pixels_failed, pixels_done
