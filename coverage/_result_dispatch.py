# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerError:
    message: str


def apply_batch_results(batch_results, loss_grid, prx_grid, itm_loss_grid,
                        clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid):
    pixels_failed = 0
    for result in batch_results:
        if result is None:
            pixels_failed += 1
        elif isinstance(result, WorkerError):
            pixels_failed += 1
            logger.warning("Coverage pixel failed in worker: %s", result.message)
        else:
            i, j, loss_db, prx, itm_loss_db, c_tx, c_rx, bel_rx = result
            loss_grid[i, j] = loss_db
            prx_grid[i, j] = prx
            itm_loss_grid[i, j] = itm_loss_db
            clutter_loss_grid[i, j] = c_tx + c_rx
            clutter_rx_db_grid[i, j] = c_rx
            bel_rx_db_grid[i, j] = bel_rx
    return pixels_failed


def log_coverage_failures(pixels_failed, total):
    if total == 0:
        return
    failure_pct = pixels_failed / max(total, 1) * 100
    if failure_pct > 50:
        logger.error("High failure rate: %.1f%% of coverage pixels failed", failure_pct)
    elif pixels_failed > 0:
        logger.warning("Coverage: %d/%d pixels failed (%.1f%%)", pixels_failed, total, failure_pct)
