# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for coverage pool close/unlink/fallback paths."""

import os
import sys
from multiprocessing.shared_memory import SharedMemory
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from NoWires.radio_coverage.pool import (
    _final_cov_pool,
    _make_shared_grid,
    _release_shared_memory,
    _get_max_workers,
)


class TestPoolSharedMemoryLifecycle:
    def test_release_shared_memory_handles_none(self):
        _release_shared_memory(None)

    def test_release_shared_memory_calls_release(self):
        grid = MagicMock()
        _release_shared_memory(grid)
        grid.release.assert_called_once()

    def test_make_shared_grid_non_empty(self):
        grid_data = np.ones((5, 5), dtype=np.float64)
        shared = _make_shared_grid(grid_data)
        assert shared is not None
        shared.release()

    def test_final_cov_pool_clears_globals(self):
        import radio_coverage.pool as rcp
        old_shm = rcp._cov_shm
        old_data = rcp._cov_grid_data
        old_meta = rcp._cov_grid_meta
        rcp._cov_shm = None
        rcp._cov_grid_data = None
        rcp._cov_grid_meta = {}
        try:
            _final_cov_pool()
            assert rcp._cov_shm is None
            assert rcp._cov_grid_data is None
        finally:
            rcp._cov_shm = old_shm
            rcp._cov_grid_data = old_data
            rcp._cov_grid_meta = old_meta

    def test_final_cov_pool_handles_shm_close_failure(self, monkeypatch):
        import radio_coverage.pool as rcp
        mock_shm = MagicMock()
        mock_shm.close.side_effect = OSError("close failed")
        mock_shm.unlink.side_effect = OSError("unlink failed")
        old_shm = rcp._cov_shm
        old_data = rcp._cov_grid_data
        rcp._cov_shm = mock_shm
        rcp._cov_grid_data = np.array([1.0])
        try:
            _final_cov_pool()
            assert rcp._cov_shm is None
        finally:
            rcp._cov_shm = old_shm
            rcp._cov_grid_data = old_data
        mock_shm.close.assert_called_once()


class TestPoolHelpers:
    def test_get_max_workers_positive(self):
        workers = _get_max_workers()
        assert workers >= 1
