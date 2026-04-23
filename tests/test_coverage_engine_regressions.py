# -*- coding: utf-8 -*-
"""Regression tests for coverage engine importability and fallback behavior."""

import importlib
import os
import py_compile
import sys
import types
from unittest.mock import MagicMock

import numpy as np


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
ENGINE_SOURCE = os.path.join(PLUGIN_DIR, "coverage_engine.py")


def test_coverage_engine_source_compiles():
    py_compile.compile(ENGINE_SOURCE, doraise=True)


def _import_coverage_engine():
    sys.modules["osgeo"] = MagicMock()
    sys.modules["osgeo.gdal"] = MagicMock()

    package = types.ModuleType("NoWires")
    package.__path__ = [PLUGIN_DIR]
    package.__package__ = "NoWires"
    package.__name__ = "NoWires"
    sys.modules["NoWires"] = package

    return importlib.import_module("NoWires.coverage_engine")


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
    coverage_engine = _import_coverage_engine()

    monkeypatch.setattr(coverage_engine, "should_use_multiprocessing", lambda: False)
    monkeypatch.setattr(
        coverage_engine,
        "_itm_worker",
        lambda task: (task[0], task[1], 123.0, -77.0),
    )

    prx_grid, loss_grid, *_ = coverage_engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=300.0,
        radius_km=0.01,
        grid_size=3,
    )

    assert prx_grid.shape == (3, 3)
    assert loss_grid.shape == (3, 3)
    assert np.nanmax(loss_grid) == 123.0
    assert np.nanmax(prx_grid) == -77.0
