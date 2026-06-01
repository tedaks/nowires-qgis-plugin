# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression tests for coverage engine importability and fallback behavior."""

import importlib
import os
import py_compile
import sys
import types
from unittest.mock import MagicMock

import numpy as np


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
ENGINE_SOURCE = os.path.join(PLUGIN_DIR, "radio_coverage/engine.py")


def test_coverage_engine_source_compiles():
    py_compile.compile(ENGINE_SOURCE, doraise=True)


def _import_coverage_engine(monkeypatch):
    # Use monkeypatch.setitem so sys.modules pollution is unwound at teardown.
    # Direct sys.modules assignment leaks MagicMock("osgeo") into the rest of
    # the test session and causes later tests (e.g. test_p2p_outputs_lon_wrap)
    # to receive a MagicMock SpatialReference, which OGR's C code accepts
    # then loops inside CreateLayer until the OOM killer fires.
    monkeypatch.setitem(sys.modules, "osgeo", MagicMock())
    monkeypatch.setitem(sys.modules, "osgeo.gdal", MagicMock())

    package = types.ModuleType("NoWires")
    package.__path__ = [PLUGIN_DIR]
    package.__package__ = "NoWires"
    package.__name__ = "NoWires"
    monkeypatch.setitem(sys.modules, "NoWires", package)

    engine = importlib.import_module("NoWires.radio_coverage.engine")
    executor = importlib.import_module("NoWires.radio_coverage._executor")
    return engine, executor


class _DummyGrid:
    def __init__(self):
        self.data = np.zeros((2, 2), dtype=np.float32)

    def grid_meta_dict(self):
        return {
            "min_lat": -0.001,
            "max_lat": 0.001,
            "min_lon": -0.001,
            "max_lon": 0.001,
            "n_lat": 2,
            "n_lon": 2,
        }


def test_compute_coverage_runs_in_single_process_mode(monkeypatch):
    coverage_engine, coverage_executor = _import_coverage_engine(monkeypatch)

    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: False)
    monkeypatch.setattr(
        coverage_executor,
        "_itm_worker",
        lambda task, **_kw: (task[0], task[1], 123.0, -77.0, 120.0, 2.0, 1.0, 0.0),
    )

    result = coverage_engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=300.0,
        radius_km=0.01,
        grid_size=3,
    )

    assert result.prx_grid.shape == (3, 3)
    assert result.loss_grid.shape == (3, 3)
    assert np.nanmax(result.loss_grid) == 123.0
    assert np.nanmax(result.prx_grid) == -77.0


def test_compute_coverage_cleans_shared_memory_when_cancelled(monkeypatch):
    coverage_engine, coverage_executor = _import_coverage_engine(monkeypatch)

    class FakeSharedGrid:
        def __init__(self):
            self.name = "fake_shared_memory"
            self._closed = False
            self._unlinked = False

        @property
        def shm(self):
            return self

        def close(self):
            self._closed = True

        def unlink(self):
            self._unlinked = True

        def release(self):
            self.close()
            self.unlink()

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, *args, **kwargs):
            yield []

    class CancelledFeedback:
        def pushInfo(self, message):
            pass

        def isCanceled(self):
            return True

    fake_grid = FakeSharedGrid()
    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: True)
    monkeypatch.setattr(coverage_executor, "_make_shared_grid", lambda grid: fake_grid)
    monkeypatch.setattr(coverage_executor, "ProcessPoolExecutor", FakeExecutor)

    result = coverage_engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=300.0,
        radius_km=0.01,
        grid_size=3,
        feedback=CancelledFeedback(),
    )

    assert result is None
    assert fake_grid._closed is True
    assert fake_grid._unlinked is True


def test_compute_coverage_falls_back_on_pool_error_and_cleans_shared_memory(monkeypatch):
    """When the process pool raises any exception (including ValueError),
    compute_coverage should fall back to sequential mode, clean up shared
    memory, and still produce a valid result.
    """
    coverage_engine, coverage_executor = _import_coverage_engine(monkeypatch)

    class FakeSharedGrid:
        def __init__(self):
            self.name = "fake_shared_memory"
            self._closed = False
            self._unlinked = False

        @property
        def shm(self):
            return self

        def close(self):
            self._closed = True

        def unlink(self):
            self._unlinked = True

        def release(self):
            self.close()
            self.unlink()

    class ExplodingExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, *args, **kwargs):
            raise ValueError("unexpected worker serialization failure")

    fake_grid = FakeSharedGrid()
    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: True)
    monkeypatch.setattr(coverage_executor, "_make_shared_grid", lambda grid: fake_grid)
    monkeypatch.setattr(coverage_executor, "ProcessPoolExecutor", ExplodingExecutor)
    monkeypatch.setattr(
        coverage_executor,
        "_itm_worker",
        lambda task, **_kw: (task[0], task[1], 123.0, -77.0, 120.0, 2.0, 1.0, 0.0),
    )

    # ValueError from the pool is now caught and triggers sequential fallback,
    # so compute_coverage returns a valid result instead of propagating the exception.
    result = coverage_engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=300.0,
        radius_km=0.01,
        grid_size=3,
    )

    # Should have fallen back to sequential mode and produced valid grids
    assert result.prx_grid is not None
    assert result.loss_grid is not None
    assert result.prx_grid.shape == (3, 3)
    # Shared grid must be cleaned up even on pool failure
    assert fake_grid._closed is True
    assert fake_grid._unlinked is True
