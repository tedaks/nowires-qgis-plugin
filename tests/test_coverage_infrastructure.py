# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests covering radio_coverage/pool.py, radio_coverage/_executor.py, and
radio_coverage/result_dispatch.py."""

from unittest.mock import MagicMock, patch

import numpy as np

from NoWires.radio_coverage._executor import execute_coverage_tasks
from NoWires.radio_coverage.result_dispatch import apply_batch_results
from NoWires.radio_coverage.pool import _make_shared_grid, _release_shared_memory


def _make_grids(n):
    grid_data = np.zeros((n, n), dtype=np.float32)
    grid_meta = {
        "tx_lat": 0.0,
        "tx_lon": 0.0,
        "min_lat": -1.0,
        "max_lat": 1.0,
        "min_lon": -1.0,
        "max_lon": 1.0,
        "n_lat": n,
        "n_lon": n,
    }
    loss_grid = np.full((n, n), np.nan)
    prx_grid = np.full((n, n), np.nan)
    itm_loss_grid = np.full((n, n), np.nan)
    clutter_loss_grid = np.full((n, n), np.nan)
    clutter_rx_db_grid = np.full((n, n), np.nan)
    bel_rx_db_grid = np.full((n, n), np.nan)
    feedback = MagicMock()
    return (
        grid_data, grid_meta, feedback,
        loss_grid, prx_grid, itm_loss_grid, clutter_loss_grid,
        clutter_rx_db_grid, bel_rx_db_grid,
    )


class TestExecutorHandlesEmptyTaskList:
    def test_executor_handles_empty_task_list(self):
        n = 10
        (
            grid_data, grid_meta, feedback,
            loss_grid, prx_grid, itm_loss_grid, clutter_loss_grid,
            clutter_rx_db_grid, bel_rx_db_grid,
        ) = _make_grids(n)

        cancelled, pixels_failed, pixels_done = execute_coverage_tasks(
            [], grid_data, grid_meta, feedback,
            loss_grid, prx_grid, itm_loss_grid, clutter_loss_grid,
            clutter_rx_db_grid, bel_rx_db_grid,
        )
        assert cancelled is False
        assert pixels_failed == 0
        assert pixels_done == 0


class TestExecutorPropagatesWorkerException:
    def test_executor_propagates_worker_exception(self):
        n = 10
        (
            grid_data, grid_meta, feedback,
            loss_grid, prx_grid, itm_loss_grid, clutter_loss_grid,
            clutter_rx_db_grid, bel_rx_db_grid,
        ) = _make_grids(n)
        task = (0, 0, 50.0, 10.0, 5000.0, 90.0,
                30.0, 100, 30.0, 10.0, 1, 301.0,
                300.0, 0, 15.0, 0.005,
                50.0, 50.0, 50.0,
                36.0, "omni", 2.0,
                2.0, 3.0, 1.0)

        with patch(
            "NoWires.radio_coverage._executor.should_use_multiprocessing", return_value=True,
        ), patch(
            "NoWires.radio_coverage._executor.ProcessPoolExecutor",
        ) as mock_ppe, patch(
            "NoWires.radio_coverage._executor.ensure_spawn_start_method",
        ), patch(
            "NoWires.radio_coverage._executor.configure_macos_multiprocessing",
        ), patch(
            "NoWires.radio_coverage._executor.configure_windows_multiprocessing",
        ), patch(
            "NoWires.radio_coverage._executor._make_shared_grid",
            return_value=MagicMock(),
        ), patch(
            "NoWires.radio_coverage._executor._release_shared_memory",
        ), patch(
            "NoWires.radio_coverage._executor._run_sequential",
            return_value=(False, 0, 0),
        ) as mock_seq:
            mock_ppe.return_value.__enter__.side_effect = RuntimeError(
                "Test forced worker error"
            )

            cancelled, pixels_failed, pixels_done = execute_coverage_tasks(
                [task], grid_data, grid_meta, feedback,
                loss_grid, prx_grid, itm_loss_grid, clutter_loss_grid,
                clutter_rx_db_grid, bel_rx_db_grid,
            )

        assert mock_seq.called, (
            "Sequential fallback must be invoked after multiprocessing failure"
        )
        assert cancelled is False
        assert pixels_failed == 0
        assert pixels_done == 0


class TestResultDispatchWithAllKeysPresent:
    def test_result_dispatch_with_all_keys_present(self):
        n = 5
        loss_grid = np.full((n, n), np.nan)
        prx_grid = np.full((n, n), np.nan)
        itm_loss_grid = np.full((n, n), np.nan)
        clutter_loss_grid = np.full((n, n), np.nan)
        clutter_rx_db_grid = np.full((n, n), np.nan)
        bel_rx_db_grid = np.full((n, n), np.nan)

        results = [
            (0, 0, -50.0, -80.0, -120.0, 5.0, 3.0, 1.0),
            (1, 1, -60.0, -90.0, -130.0, 6.0, 4.0, 2.0),
            (2, 2, -70.0, -100.0, -140.0, 7.0, 5.0, 3.0),
        ]

        failed = apply_batch_results(
            results, loss_grid, prx_grid, itm_loss_grid,
            clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid,
        )
        assert failed == 0
        assert loss_grid[0, 0] == -50.0
        assert prx_grid[0, 0] == -80.0
        assert itm_loss_grid[0, 0] == -120.0
        assert clutter_loss_grid[0, 0] == 8.0
        assert clutter_rx_db_grid[0, 0] == 3.0
        assert bel_rx_db_grid[0, 0] == 1.0

        assert loss_grid[1, 1] == -60.0
        assert prx_grid[1, 1] == -90.0
        assert itm_loss_grid[1, 1] == -130.0
        assert clutter_loss_grid[1, 1] == 10.0
        assert clutter_rx_db_grid[1, 1] == 4.0
        assert bel_rx_db_grid[1, 1] == 2.0

        assert loss_grid[2, 2] == -70.0
        assert prx_grid[2, 2] == -100.0
        assert itm_loss_grid[2, 2] == -140.0
        assert clutter_loss_grid[2, 2] == 12.0
        assert clutter_rx_db_grid[2, 2] == 5.0
        assert bel_rx_db_grid[2, 2] == 3.0


class TestPoolCreatesAndJoins:
    def test_pool_creates_and_joins(self):
        data = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        shared_grid = _make_shared_grid(data)
        assert shared_grid is not None
        _release_shared_memory(shared_grid)

    def test_pool_lifecycle_release_none_is_noop(self):
        _release_shared_memory(None)
