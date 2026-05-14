# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for shared_dem_grid.py — error paths and edge cases."""

import multiprocessing
import multiprocessing.shared_memory

import numpy as np
import pytest

try:
    multiprocessing.shared_memory.SharedMemory(create=True, size=4, name="pytest_sdg_ext_chk")
    _shim = multiprocessing.shared_memory.SharedMemory(name="pytest_sdg_ext_chk")
    _shim.close()
    _shim.unlink()
    _HAS_SHARED_MEMORY = True
except Exception:
    _HAS_SHARED_MEMORY = False

requires_shared_memory = pytest.mark.skipif(
    not _HAS_SHARED_MEMORY,
    reason="multiprocessing.shared_memory not available",
)

from NoWires.shared_dem_grid import SharedDEMGrid


@requires_shared_memory
class TestSharedDEMGridDoubleRelease:
    def test_double_release_is_safe(self):
        data = np.zeros(5, dtype=np.float32)
        grid = SharedDEMGrid(data)
        grid.release()
        grid.release()
        assert grid.shm is None

    def test_context_manager_then_explicit_release(self):
        data = np.arange(3, dtype=np.float32)
        with SharedDEMGrid(data) as grid:
            assert grid.shm is not None
            grid.release()
            assert grid.shm is None
        assert grid.shm is None

    def test_unlinked_flag_prevents_double_unlink(self):
        data = np.zeros(3, dtype=np.float32)
        grid = SharedDEMGrid(data)
        grid._unlinked = True
        grid.release()
        assert grid._unlinked is True


@requires_shared_memory
class TestSharedDEMGridAtexit:
    def test_atexit_cleanup_runs_and_is_idempotent(self):
        data = np.zeros(3, dtype=np.float32)
        grid = SharedDEMGrid(data)
        grid._atexit_cleanup()
        assert grid.shm is None
        grid._atexit_cleanup()
        assert grid.shm is None

    def test_atexit_unregistered_on_release(self):
        data = np.zeros(3, dtype=np.float32)
        grid = SharedDEMGrid(data)
        grid.release()
        assert grid.shm is None
        assert grid.name is None
