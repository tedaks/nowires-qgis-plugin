# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for coverage_pool — apply_batch_results, log_coverage_failures,
_ensure_path, should_use_multiprocessing, _itm_worker, _itm_worker_batch,
and shared-memory helpers."""

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from NoWires.coverage.pool import (
    _CoverageTask,
    apply_batch_results,
    log_coverage_failures,
    should_use_multiprocessing,
    _ensure_path,
    _interpolate_nan_elevations,
    _make_shared_grid,
    _release_shared_memory,
    _itm_worker,
    _itm_worker_batch,
    _final_cov_pool,
)
from NoWires.coverage._result_dispatch import WorkerError


class TestInterpolateNANElevations:
    def test_delegates_to_nan_utils(self):
        arr = np.array([1.0, np.nan, 3.0])
        result = _interpolate_nan_elevations(arr)
        assert not np.isnan(result).any()
        assert result[1] == pytest.approx(2.0)

    def test_all_nan_unchanged(self):
        arr = np.array([np.nan, np.nan, np.nan])
        result = _interpolate_nan_elevations(arr)
        assert np.isnan(result).all()

    def test_no_nan_unchanged(self):
        arr = np.array([1.0, 2.0, 3.0])
        result = _interpolate_nan_elevations(arr)
        np.testing.assert_array_equal(result, arr)


class TestShouldUseMultiprocessing:
    def test_nt_returns_false(self):
        assert should_use_multiprocessing(os_name="nt") is False

    def test_posix_returns_true(self):
        assert should_use_multiprocessing(os_name="posix", platform_name="linux") is True

    def test_darwin_falls_back_when_no_python_exe(self):
        with patch.object(sys, "platform", "darwin"), \
             patch("NoWires.coverage.pool.find_macos_python_executable", return_value=None):
            result = should_use_multiprocessing()
            assert result is False

    def test_darwin_returns_true_when_python_exe_found(self):
        with patch.object(sys, "platform", "darwin"), \
             patch("NoWires.coverage.pool.find_macos_python_executable", return_value="/usr/bin/python3"):
            result = should_use_multiprocessing()
            assert result is True

    def test_default_uses_os_name(self):
        with patch.object(os, "name", "nt"):
            assert should_use_multiprocessing() is False


class TestEnsurePath:
    def test_adds_plugin_dir_to_sys_path(self):
        original_path = list(sys.path)
        try:
            _ensure_path()
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            assert plugin_dir in sys.path
        finally:
            sys.path[:] = original_path


class TestFinalCovPool:
    def test_cleans_up_shared_memory_on_shutdown(self):
        mock_shm = MagicMock()
        import NoWires.coverage.pool as cp
        cp._cov_shm = mock_shm
        cp._cov_grid_data = np.array([1.0, 2.0])
        try:
            _final_cov_pool()
            assert cp._cov_shm is None
            assert cp._cov_grid_data is None
        finally:
            cp._cov_shm = None
            cp._cov_grid_data = None

    def test_noop_when_nothing_to_clean(self):
        import NoWires.coverage.pool as cp
        cp._cov_shm = None
        cp._cov_grid_data = None
        _final_cov_pool()
        assert cp._cov_shm is None


class TestApplyBatchResults:
    def test_all_successful_results(self):
        n = 3
        loss = np.full((n, n), np.nan)
        prx = np.full((n, n), np.nan)
        itm_loss = np.full((n, n), np.nan)
        clutter_loss = np.full((n, n), np.nan)
        clutter_rx = np.full((n, n), np.nan)
        bel_rx = np.full((n, n), np.nan)

        results = [
            (0, 0, 120.0, -50.0, 115.0, 2.0, 3.0, 1.0),
            (0, 1, 130.0, -60.0, 125.0, 2.0, 3.0, 1.0),
            (1, 0, 140.0, -70.0, 135.0, 2.0, 3.0, 1.0),
        ]

        failed = apply_batch_results(
            results, loss, prx, itm_loss, clutter_loss, clutter_rx, bel_rx,
        )
        assert failed == 0
        assert loss[0, 0] == 120.0
        assert prx[0, 0] == -50.0
        assert itm_loss[0, 0] == 115.0
        assert clutter_loss[0, 1] == 5.0
        assert clutter_rx[1, 0] == 3.0
        assert bel_rx[0, 0] == 1.0

    def test_none_result_increments_failure_count(self):
        n = 2
        loss = np.full((n, n), np.nan)
        prx = np.full((n, n), np.nan)
        itm_loss = np.full((n, n), np.nan)
        clutter_loss = np.full((n, n), np.nan)
        clutter_rx = np.full((n, n), np.nan)
        bel_rx = np.full((n, n), np.nan)

        results = [(0, 0, 120.0, -50.0, 115.0, 2.0, 3.0, 1.0), None]

        failed = apply_batch_results(
            results, loss, prx, itm_loss, clutter_loss, clutter_rx, bel_rx,
        )
        assert failed == 1

    def test_worker_error_increments_failure_count(self):
        n = 2
        loss = np.full((n, n), np.nan)
        prx = np.full((n, n), np.nan)
        itm_loss = np.full((n, n), np.nan)
        clutter_loss = np.full((n, n), np.nan)
        clutter_rx = np.full((n, n), np.nan)
        bel_rx = np.full((n, n), np.nan)

        results = [WorkerError("something broke")]

        failed = apply_batch_results(
            results, loss, prx, itm_loss, clutter_loss, clutter_rx, bel_rx,
        )
        assert failed == 1

    def test_empty_results_returns_zero(self):
        loss = np.zeros((1, 1))
        prx = np.zeros((1, 1))
        failed = apply_batch_results(
            [], loss, prx, loss, loss, loss, loss,
        )
        assert failed == 0


class TestLogCoverageFailures:
    def test_zero_total_returns_immediately(self, caplog):
        with caplog.at_level(logging.WARNING):
            log_coverage_failures(1, 0)
        assert len(caplog.records) == 0

    def test_high_failure_rate_logs_error(self, caplog):
        with caplog.at_level(logging.ERROR):
            log_coverage_failures(80, 100)
        assert any("High failure rate" in r.message for r in caplog.records)

    def test_moderate_failure_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            log_coverage_failures(10, 100)
        assert any("pixels failed" in r.message for r in caplog.records)

    def test_no_failures_logs_nothing(self, caplog):
        with caplog.at_level(logging.WARNING):
            log_coverage_failures(0, 100)
        assert len(caplog.records) == 0


class TestCoverageTask:
    def test_creates_task_from_args(self):
        args = (
            0, 1, 50.0, 10.0, 5000.0, 90.0,
            30.0, 100, 30.0, 10.0, 1, 301.0,
            300.0, 0, 15.0, 0.005,
            50.0, 50.0, 50.0,
            36.0, "omni", 2.0,
            2.0, 3.0, 1.0,
        )
        task = _CoverageTask(*args)
        assert task.i == 0
        assert task.j == 1
        assert task.target_lat == 50.0
        assert task.target_lon == 10.0
        assert task.dist_m == 5000.0
        assert task.clutter_tx_db == 2.0
        assert task.clutter_rx_db == 3.0
        assert task.bel_rx_db == 1.0


class TestITMWorkerNANHandling:
    def test_all_nan_elevations_returns_none(self):
        with patch("NoWires.coverage.pool.sample_line_from_grid",
                   return_value=np.array([np.nan, np.nan, np.nan])):
            grid_data = np.zeros((10, 10))
            grid_meta = {
                "tx_lat": 0.0, "tx_lon": 0.0,
                "min_lat": -1.0, "max_lat": 1.0,
                "min_lon": -1.0, "max_lon": 1.0,
                "n_lat": 10, "n_lon": 10,
            }
            task = _CoverageTask(
                0, 0, 50.0, 10.0, 5000.0, 90.0,
                30.0, 50, 30.0, 10.0, 1, 301.0,
                300.0, 0, 15.0, 0.005,
                50.0, 50.0, 50.0,
                36.0, "omni", 2.0,
                0.0, 0.0, 0.0,
            )
            result = _itm_worker(
                tuple(task),
                grid_data=grid_data,
                grid_meta=grid_meta,
            )
            assert result is None


class TestITMWorkerBatch:
    def test_returns_results_for_all_tasks(self):
        task1 = _CoverageTask(
            0, 0, 50.0, 10.0, 5000.0, 90.0,
            30.0, 50, 30.0, 10.0, 1, 301.0,
            300.0, 0, 15.0, 0.005,
            50.0, 50.0, 50.0,
            36.0, "omni", 2.0,
            0.0, 0.0, 0.0,
        )
        task2 = _CoverageTask(
            0, 1, 51.0, 11.0, 6000.0, 45.0,
            30.0, 50, 30.0, 10.0, 1, 301.0,
            300.0, 0, 15.0, 0.005,
            50.0, 50.0, 50.0,
            36.0, "omni", 2.0,
            0.0, 0.0, 0.0,
        )

        with patch("NoWires.coverage.pool.sample_line_from_grid",
                   return_value=np.array([np.nan, np.nan, np.nan])):
            batch = [tuple(task1), tuple(task2)]
            # v1.5.5+: _itm_worker_batch takes a plain batch list (no
            # cross-process cancel event — see test_coverage_executor_spawn_safety).
            results = _itm_worker_batch(batch)
            assert len(results) == 2

    def test_takes_plain_batch_argument(self):
        """The function signature must accept a plain list of task tuples.

        Earlier versions of v1.5.5 took a (batch, cancel_event) tuple under
        Manager().Event(); both that and the prior plain Event() approach
        failed on macOS QGIS, so the cancel-event arg was removed entirely.
        """
        task = _CoverageTask(
            0, 0, 50.0, 10.0, 5000.0, 90.0,
            30.0, 50, 30.0, 10.0, 1, 301.0,
            300.0, 0, 15.0, 0.005,
            50.0, 50.0, 50.0,
            36.0, "omni", 2.0,
            0.0, 0.0, 0.0,
        )
        batch = [tuple(task), tuple(task)]

        with patch("NoWires.coverage.pool.sample_line_from_grid",
                   return_value=np.array([np.nan, np.nan, np.nan])):
            results = _itm_worker_batch(batch)
            assert len(results) == 2


class TestSharedMemoryHelpers:
    def test_make_shared_grid(self):
        data = np.array([1.0, 2.0, 3.0])
        grid = _make_shared_grid(data)
        assert grid is not None

    def test_release_shared_memory_with_none(self):
        _release_shared_memory(None)

    def test_release_shared_memory_with_grid(self):
        mock_grid = MagicMock()
        _release_shared_memory(mock_grid)
        mock_grid.release.assert_called_once()
