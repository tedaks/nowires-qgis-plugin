# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for v1.5.6 multiprocessing pickling bug.

Reported on Windows after the v1.5.5 pythonw.exe switch made the MP gate
succeed where it had been silently returning None:

    _pickle.PicklingError: Can't pickle <function _init_cov_pool at 0x...>:
    it's not the same object as NoWires.coverage_pool._init_cov_pool

Cause: ``_coverage_executor`` captured ``_init_cov_pool`` /
``_itm_worker_batch`` at module import time via ``from .coverage_pool
import ...``. If anything subsequently replaced ``NoWires.coverage_pool``
in ``sys.modules`` (QGIS plugin reload, the Plugin Reloader plugin, any
manual ``importlib.reload``), the cached attribute on the executor module
diverged from ``sys.modules["NoWires.coverage_pool"].<name>``, and
``pickle``'s identity check raised.

Fix: resolve both functions through the package import at call time, so
the references handed to ``ProcessPoolExecutor`` are exactly the ones
``pickle`` finds via ``getattr(sys.modules[fn.__module__], fn.__qualname__)``.
"""

import importlib
import os
import pickle
import sys

import numpy as np


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


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


def _capturing_executor():
    """Return a fake ProcessPoolExecutor that records ctor + map() args."""
    captured = {}

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            captured["initializer"] = kwargs.get("initializer")
            captured["initargs"] = kwargs.get("initargs")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, fn, chunks, chunksize=1):
            captured["map_fn"] = fn
            yield from ()

    return FakeExecutor, captured


def test_executor_handles_coverage_pool_reload(monkeypatch):
    """After ``importlib.reload(coverage_pool)``, the executor must hand
    pickle-resolvable function objects to ProcessPoolExecutor.

    Without the fix, ``_coverage_executor`` would still reference the
    pre-reload functions; pickle would compare them against the new
    module's attributes and raise PicklingError.
    """
    coverage_engine = importlib.import_module("NoWires.coverage_engine")
    coverage_executor = importlib.import_module("NoWires._coverage_executor")
    coverage_pool = importlib.import_module("NoWires.coverage_pool")

    # Simulate a reload: replace the in-cache module with a freshly
    # executed version. The functions on the new module are distinct
    # Python objects from the pre-reload ones still cached on
    # _coverage_executor's globals (if it had imported them by name).
    coverage_pool = importlib.reload(coverage_pool)
    sys.modules["NoWires.coverage_pool"] = coverage_pool

    class _FakeSharedGrid:
        def __init__(self):
            self.name = "shm_reload_regression"

        @property
        def shm(self):
            return self

        def close(self):
            pass

        def unlink(self):
            pass

        def release(self):
            pass

    FakeExecutor, captured = _capturing_executor()
    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: True)
    monkeypatch.setattr(coverage_executor, "_make_shared_grid", lambda grid: _FakeSharedGrid())
    monkeypatch.setattr(coverage_executor, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(coverage_executor, "configure_macos_multiprocessing", lambda: None)
    monkeypatch.setattr(coverage_executor, "configure_windows_multiprocessing", lambda: None)
    monkeypatch.setattr(coverage_executor, "ensure_spawn_start_method", lambda: None)

    coverage_engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=300.0,
        radius_km=0.01,
        grid_size=3,
    )

    # The functions handed to ProcessPoolExecutor must be the SAME OBJECTS
    # as those on the (reloaded) coverage_pool module — that's what pickle
    # checks via getattr(sys.modules[fn.__module__], fn.__qualname__) is fn.
    assert captured["initializer"] is coverage_pool._init_cov_pool, (
        "executor passed a stale _init_cov_pool reference; pickle would "
        "raise PicklingError on Windows/macOS spawn"
    )
    assert captured["map_fn"] is coverage_pool._itm_worker_batch, (
        "executor passed a stale _itm_worker_batch reference; pickle would "
        "raise PicklingError on Windows/macOS spawn"
    )


def test_init_cov_pool_picklable_after_reload():
    """Direct pickle check: after reload, the module's functions must
    survive ``pickle.dumps`` in the parent process. This is the exact
    operation ProcessPoolExecutor performs when spawning a worker.
    """
    coverage_pool = importlib.import_module("NoWires.coverage_pool")
    coverage_pool = importlib.reload(coverage_pool)
    sys.modules["NoWires.coverage_pool"] = coverage_pool

    # Both functions need to be picklable by reference for spawn workers.
    pickle.dumps(coverage_pool._init_cov_pool)
    pickle.dumps(coverage_pool._itm_worker_batch)


def test_executor_does_not_import_init_cov_pool_at_module_level():
    """Lock in the lazy-lookup contract: importing the functions at module
    level would resurrect the bug. ``_coverage_executor`` must reach them
    through the package at call time instead.
    """
    src_path = os.path.join(PLUGIN_DIR, "_coverage_executor.py")
    with open(src_path, "r", encoding="utf-8") as f:
        src = f.read()
    # Strip comment lines so docstrings/comments mentioning the names
    # for context don't trip the contract.
    code = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    assert "_init_cov_pool" not in code.split("def execute_coverage_tasks")[0], (
        "_init_cov_pool must not be imported at module scope — it has to be "
        "resolved through sys.modules at call time so reloads of "
        "coverage_pool don't break pickle's identity check."
    )
    assert "_itm_worker_batch" not in code.split("def execute_coverage_tasks")[0], (
        "_itm_worker_batch must not be imported at module scope (same reason)."
    )
