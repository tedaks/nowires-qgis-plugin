# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: BEL must work independently of clutter_enabled."""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock

import numpy as np

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _import_engine(monkeypatch):
    package = types.ModuleType("NoWires")
    package.__path__ = [PLUGIN_DIR]
    package.__package__ = "NoWires"
    package.__name__ = "NoWires"
    monkeypatch.setitem(sys.modules, "NoWires", package)
    return importlib.import_module("NoWires.radio_coverage.engine")


class _DummyGrid:
    def __init__(self):
        self.data = np.zeros((4, 4), dtype=np.float32)

    @staticmethod
    def grid_meta_dict():
        return {
            "min_lat": -0.001,
            "max_lat": 0.001,
            "min_lon": -0.001,
            "max_lon": 0.001,
            "n_lat": 4,
            "n_lon": 4,
        }


def test_coverage_bel_without_clutter(monkeypatch):
    """BEL must apply when clutter_enabled=False but bel_enabled=True."""
    engine = _import_engine(monkeypatch)

    import radio_coverage._executor as coverage_executor
    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: False)

    bel_rec = []

    def worker(task, **_kw):
        bel_rx_db = task.bel_rx_db
        bel_rec.append(bel_rx_db)
        prx = -77.0 - bel_rx_db
        return (task[0], task[1], 123.0, prx, 120.0, 2.0, 1.0, bel_rx_db)

    monkeypatch.setattr(coverage_executor, "_itm_worker", worker)

    feedback = MagicMock()
    feedback.isCanceled = lambda: False

    engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=900.0,
        radius_km=0.1,
        grid_size=4,
        clutter_enabled=False,
        bel_enabled=True,
        bel_building_type="traditional",
        bel_elevation_angle_deg=15.0,
        feedback=feedback,
    )

    assert any(b != 0.0 for b in bel_rec), (
        "All bel_rx_db values are zero when clutter_enabled=False, bel_enabled=True"
    )


def test_coverage_bel_disabled_zero(monkeypatch):
    """BEL must be zero when bel_enabled=False (even if clutter is on)."""
    engine = _import_engine(monkeypatch)

    import radio_coverage._executor as coverage_executor
    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: False)

    bel_rec = []

    def worker(task, **_kw):
        bel_rx_db = task.bel_rx_db
        bel_rec.append(bel_rx_db)
        prx = -77.0
        return (task[0], task[1], 123.0, prx, 120.0, 2.0, 1.0, bel_rx_db)

    monkeypatch.setattr(coverage_executor, "_itm_worker", worker)

    feedback = MagicMock()
    feedback.isCanceled = lambda: False

    engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=900.0,
        radius_km=0.1,
        grid_size=4,
        clutter_enabled=True,
        clutter_model="simple",
        bel_enabled=False,
        bel_building_type="traditional",
        feedback=feedback,
    )

    assert all(b == 0.0 for b in bel_rec)