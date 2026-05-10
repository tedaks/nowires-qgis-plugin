# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for shared_dem_grid — SharedDEMGrid shared-memory lifecycle."""

import multiprocessing
import multiprocessing.shared_memory

import numpy as np
import pytest

try:
    multiprocessing.shared_memory.SharedMemory(create=True, size=4, name="pytest_avail_chk_shm")
    _shim = multiprocessing.shared_memory.SharedMemory(name="pytest_avail_chk_shm")
    _shim.close()
    _shim.unlink()
    _HAS_SHARED_MEMORY = True
except Exception:
    _HAS_SHARED_MEMORY = False

requires_shared_memory = pytest.mark.skipif(
    not _HAS_SHARED_MEMORY,
    reason="multiprocessing.shared_memory not available",
)

from shared_dem_grid import SharedDEMGrid


@requires_shared_memory
class TestSharedDEMGridCreation:
    def test_float32_array_data_copied(self):
        data = np.arange(12, dtype=np.float32).reshape(3, 4)
        grid = SharedDEMGrid(data)
        try:
            assert grid.shm is not None
            assert grid.name is not None
            assert isinstance(grid.name, str)
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            np.testing.assert_array_equal(result, data)
        finally:
            grid.release()

    def test_float64_array_data_copied(self):
        data = np.linspace(0, 1, 10, dtype=np.float64)
        grid = SharedDEMGrid(data)
        try:
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            np.testing.assert_array_equal(result, data)
        finally:
            grid.release()

    def test_int16_array_data_copied(self):
        data = np.array([[100, 200], [300, 400]], dtype=np.int16)
        grid = SharedDEMGrid(data)
        try:
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            np.testing.assert_array_equal(result, data)
        finally:
            grid.release()


@requires_shared_memory
class TestSharedDEMGridRelease:
    def test_release_clears_shm_and_name(self):
        data = np.zeros(5, dtype=np.float32)
        grid = SharedDEMGrid(data)
        assert grid.shm is not None
        assert grid.name is not None
        grid.release()
        assert grid.shm is None
        assert grid.name is None

    def test_release_is_idempotent(self):
        data = np.zeros(5, dtype=np.float32)
        grid = SharedDEMGrid(data)
        grid.release()
        grid.release()
        assert grid.shm is None
        assert grid.name is None


@requires_shared_memory
class TestSharedDEMGridContextManager:
    def test_context_manager_data_available_and_released(self):
        data = np.arange(6, dtype=np.float32)
        with SharedDEMGrid(data) as grid:
            assert grid.shm is not None
            assert grid.name is not None
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            np.testing.assert_array_equal(result, data)
        assert grid.shm is None
        assert grid.name is None


@requires_shared_memory
class TestSharedDEMGridDataIntegrity:
    def test_shared_memory_matches_input_exactly(self):
        data = np.array([1.5, -2.3, 0.0, 999.9], dtype=np.float32)
        grid = SharedDEMGrid(data)
        try:
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            np.testing.assert_array_equal(result, data)
            assert result.dtype == data.dtype
        finally:
            grid.release()


@requires_shared_memory
class TestSharedDEMGridShapes:
    def test_2d_array(self):
        data = np.arange(20, dtype=np.float64).reshape(4, 5)
        grid = SharedDEMGrid(data)
        try:
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            assert result.shape == data.shape
            np.testing.assert_array_equal(result, data)
        finally:
            grid.release()

    def test_1d_array(self):
        data = np.array([10, 20, 30], dtype=np.int32)
        grid = SharedDEMGrid(data)
        try:
            result = np.ndarray(data.shape, dtype=data.dtype, buffer=grid.shm.buf)
            assert result.shape == data.shape
            np.testing.assert_array_equal(result, data)
        finally:
            grid.release()