# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test: BEL is applied in simple-clutter mode, not just advanced."""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest

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
        self.data = np.zeros((2, 2), dtype=np.float32)

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


def _run_coverage(engine, monkeypatch, bel_enabled, bel_rec):
    import radio_coverage._executor as coverage_executor

    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: False)

    def worker(task, **_kw):
        bel_rx_db = task[24]
        bel_rec.append(bel_rx_db)
        prx = -77.0 - bel_rx_db
        return (task[0], task[1], 123.0, prx, 120.0, 2.0, 1.0, bel_rx_db)

    monkeypatch.setattr(coverage_executor, "_itm_worker", worker)

    feedback = MagicMock()
    feedback.isCanceled = lambda: False

    return engine.compute_coverage(
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
        bel_enabled=bel_enabled,
        bel_building_type="traditional",
        bel_elevation_angle_deg=15.0,
        feedback=feedback,
    )


def test_simple_mode_honors_bel(monkeypatch):
    engine = _import_engine(monkeypatch)

    bel_no = []
    result_no_bel = _run_coverage(engine, monkeypatch, bel_enabled=False, bel_rec=bel_no)
    mean_no_bel = np.nanmean(result_no_bel.prx_grid)

    bel_yes = []
    result_with_bel = _run_coverage(engine, monkeypatch, bel_enabled=True, bel_rec=bel_yes)
    mean_with_bel = np.nanmean(result_with_bel.prx_grid)

    assert mean_no_bel != pytest.approx(mean_with_bel, abs=0.1), (
        "mean Prx should differ when BEL is enabled vs disabled in simple mode"
    )
    assert any(b != 0.0 for b in bel_yes), (
        "at least one task should have non-zero bel_rx_db when BEL is enabled"
    )
    assert all(b == 0.0 for b in bel_no), (
        "all tasks should have zero bel_rx_db when BEL is disabled"
    )
