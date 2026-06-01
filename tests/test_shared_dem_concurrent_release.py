# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: concurrent SharedDEMGrid release safety."""

import gc
import os
import threading
import time
import weakref

import numpy as np
import pytest

from NoWires.shared_dem_grid import SharedDEMGrid

_posix_shm = pytest.mark.skipif(
    not os.path.exists("/dev/shm"),
    reason="/dev/shm not available on this platform",
)


class TestConcurrentRelease:
    @_posix_shm
    def test_eight_threads_release_no_double_unlink(self):
        grid_data = np.zeros((10, 10), dtype=np.float64)
        grid = SharedDEMGrid(grid_data)
        name = grid.name
        assert name is not None
        assert os.path.exists(os.path.join("/dev/shm", name))

        errors = []
        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()
            try:
                grid.release()
            except OSError as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent release raised: {errors}"
        assert not os.path.exists(os.path.join("/dev/shm", name))

    def test_release_blocks_while_lock_held(self):
        grid_data = np.zeros((10, 10), dtype=np.float64)
        grid = SharedDEMGrid(grid_data)
        name = grid.name
        hold_event = threading.Event()
        released_flag = []

        def holder():
            with grid._release_lock:
                hold_event.set()
                time.sleep(0.3)
            released_flag.append("done")

        t = threading.Thread(target=holder)
        t.start()
        hold_event.wait(timeout=1.0)

        start = time.monotonic()
        grid.release()
        elapsed = time.monotonic() - start
        t.join()

        assert elapsed >= 0.15, f"Release returned too fast: {elapsed:.3f}s"
        assert released_flag == ["done"]
        assert not os.path.exists(os.path.join("/dev/shm", name))

    @_posix_shm
    def test_del_removes_shm_segment(self):
        grid_data = np.zeros((10, 10), dtype=np.float64)
        grid = SharedDEMGrid(grid_data)
        name = grid.name
        ref = weakref.ref(grid)
        shm_path = os.path.join("/dev/shm", name)
        assert os.path.exists(shm_path)
        del grid
        gc.collect()
        assert ref() is None
        assert not os.path.exists(shm_path)


class TestSharedDemGridEdgeCases:
    def test_release_twice_is_idempotent(self):
        grid_data = np.zeros((10, 10), dtype=np.float64)
        grid = SharedDEMGrid(grid_data)
        grid.release()
        grid.release()

    @_posix_shm
    def test_context_manager_releases(self):
        grid_data = np.zeros((10, 10), dtype=np.float64)
        with SharedDEMGrid(grid_data) as grid:
            name = grid.name
            assert os.path.exists(os.path.join("/dev/shm", name))
        assert not os.path.exists(os.path.join("/dev/shm", name))
