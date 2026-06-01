# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: coverage antimeridian cell centers sweep the right direction."""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock

import numpy as np

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _import_engine(monkeypatch):
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
    data = np.zeros((2, 2), dtype=np.float32)

    @staticmethod
    def grid_meta_dict():
        return {
            "min_lat": -0.001,
            "max_lat": 0.001,
            "min_lon": -0.001,
            "max_lon": 0.001,
            "n_lat": 2,
            "n_lon": 2,
        }


def test_antimeridian_tx_produces_tasks(monkeypatch):
    """TX at lon=179.95, radius=20 km must produce >0 coverage tasks."""
    engine, executor = _import_engine(monkeypatch)

    monkeypatch.setattr(executor, "should_use_multiprocessing", lambda: False)

    tasks_record = []

    def capture_tasks(tasks, grid_data, grid_meta, feedback, *args):
        nonlocal tasks_record
        tasks_record = list(tasks)
        return False, 0, len(tasks)

    monkeypatch.setattr(engine, "execute_coverage_tasks", capture_tasks)

    feedback = MagicMock()
    feedback.isCanceled = lambda: False

    result = engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=179.95,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=900.0,
        radius_km=20.0,
        grid_size=64,
        feedback=feedback,
    )

    assert result is not None, "compute_coverage returned None for antimeridian TX"
    assert len(tasks_record) > 0, "No coverage tasks generated near antimeridian"

    lons = [t.target_lon for t in tasks_record]
    for lon in lons:
        diff = abs(((float(lon) + 180.0) % 360.0) - 180.0 - 179.95)
        diff = min(diff, abs(diff - 360.0))
        assert diff < 0.3, (
            f"Cell lon {lon:.4f} diff={diff:.4f} too far from TX lon 179.95"
        )


def test_axis_centers_wrapping_bounds():
    """When west > east (antimeridian), centers stay near the wrap, not ~359° away."""
    from NoWires.radio_coverage.tasks import _coverage_axis_centers

    centers = _coverage_axis_centers(179.5, -179.5, 8)
    for c in centers:
        normalized = ((c + 180.0) % 360.0) - 180.0
        assert abs(normalized - 180.0) < 0.6 or abs(normalized + 180.0) < 0.6, (
            f"Center {c:.4f} is too far from the antimeridian"
        )
    assert len(centers) == 8


def test_axis_centers_non_wrapping_unchanged():
    """Normal (west < east) ranges produce the same results as before."""
    from NoWires.radio_coverage.tasks import _coverage_axis_centers

    centers = _coverage_axis_centers(0.0, 10.0, 5)
    expected = np.array([1.0, 3.0, 5.0, 7.0, 9.0])
    assert np.allclose(centers, expected)