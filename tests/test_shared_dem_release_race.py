# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression tests for I8: concurrent release() race on SharedDEMGrid."""

import multiprocessing
import multiprocessing.shared_memory
import threading

import numpy as np
import pytest

try:
    multiprocessing.shared_memory.SharedMemory(create=True, size=4, name="pytest_avail_chk_shm_race")
    _shim = multiprocessing.shared_memory.SharedMemory(name="pytest_avail_chk_shm_race")
    _shim.close()
    _shim.unlink()
    _HAS_SHARED_MEMORY = True
except Exception:
    _HAS_SHARED_MEMORY = False

requires_shared_memory = pytest.mark.skipif(
    not _HAS_SHARED_MEMORY,
    reason="multiprocessing.shared_memory not available",
)


@requires_shared_memory
def test_concurrent_release_no_exception():
    """Two threads calling release() concurrently must not raise."""
    from NoWires.shared_dem_grid import SharedDEMGrid

    grid = SharedDEMGrid(np.zeros((4, 4), dtype=np.float32))
    errors = []

    def releaser():
        try:
            grid.release()
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=releaser)
    t2 = threading.Thread(target=releaser)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, f"Concurrent release raised: {errors}"
    assert grid._shm is None
    assert grid._name is None


@requires_shared_memory
def test_double_release_idempotent():
    """Two sequential release() calls must be safe (idempotent)."""
    from NoWires.shared_dem_grid import SharedDEMGrid

    grid = SharedDEMGrid(np.zeros((2, 2), dtype=np.float32))
    grid.release()
    grid.release()
    assert grid._shm is None
    assert grid._name is None


@requires_shared_memory
def test_release_under_lock_sets_unlinked():
    """After release(), _unlinked must be True and _shm must be None."""
    from NoWires.shared_dem_grid import SharedDEMGrid

    grid = SharedDEMGrid(np.zeros((2, 2), dtype=np.float32))
    assert not grid._unlinked
    grid.release()
    assert grid._unlinked is True
    assert grid._shm is None


@requires_shared_memory
def test_many_concurrent_releases():
    """Many threads all calling release() on the same SharedDEMGrid must not error."""
    from NoWires.shared_dem_grid import SharedDEMGrid

    grid = SharedDEMGrid(np.zeros((2, 2), dtype=np.float32))
    errors = []
    n = 10
    barrier = threading.Barrier(n)

    def releaser():
        try:
            barrier.wait()
            grid.release()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=releaser) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Concurrent release errors: {errors}"
    assert grid._shm is None