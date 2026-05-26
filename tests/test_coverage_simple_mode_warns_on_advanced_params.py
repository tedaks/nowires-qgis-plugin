# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test: simple-clutter mode warns when advanced-only params are set."""

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


def _run_with_params(engine, monkeypatch, feedback, **kwargs):
    import radio_coverage._executor as coverage_executor

    monkeypatch.setattr(coverage_executor, "should_use_multiprocessing", lambda: False)

    def worker(task, **_kw):
        return (task[0], task[1], 123.0, -77.0, 120.0, 2.0, 1.0, 0.0)

    monkeypatch.setattr(coverage_executor, "_itm_worker", worker)

    defaults = dict(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=900.0,
        radius_km=0.01,
        grid_size=3,
        clutter_enabled=True,
        clutter_model="simple",
        feedback=feedback,
    )
    defaults.update(kwargs)
    return engine.compute_coverage(**defaults)


def test_simple_mode_warns_on_advanced_percentile(monkeypatch):
    """feedback.pushWarning must be called when percentile is non-default in simple mode."""
    engine = _import_engine(monkeypatch)
    feedback = MagicMock()

    _run_with_params(engine, monkeypatch, feedback, clutter_percentile=90.0)

    warnings = [
        call[0][0]
        for call in feedback.pushWarning.call_args_list
    ]
    assert any(
        "CLUTTER_PERCENTILE" in msg and "90.0" in msg and "ignored" in msg
        for msg in warnings
    ), f"Expected percentile warning, got: {warnings}"


def test_simple_mode_warns_on_bel_enabled(monkeypatch):
    """feedback.pushWarning must be called when BEL is enabled in simple mode."""
    engine = _import_engine(monkeypatch)
    feedback = MagicMock()

    _run_with_params(engine, monkeypatch, feedback, bel_enabled=True)

    warnings = [
        call[0][0]
        for call in feedback.pushWarning.call_args_list
    ]
    assert any(
        "BEL_ENABLED" in msg and "ignored" in msg
        for msg in warnings
    ), f"Expected BEL warning, got: {warnings}"


def test_simple_mode_warns_on_tx_clutter_override(monkeypatch):
    """feedback.pushWarning must be called when tx_clutter_override is set in simple mode."""
    engine = _import_engine(monkeypatch)
    feedback = MagicMock()

    _run_with_params(engine, monkeypatch, feedback, tx_clutter_override="urban")

    warnings = [
        call[0][0]
        for call in feedback.pushWarning.call_args_list
    ]
    assert any(
        "TX_CLUTTER_OVERRIDE" in msg and "ignored" in msg
        for msg in warnings
    ), f"Expected TX override warning, got: {warnings}"


def test_simple_mode_no_warning_on_default_params(monkeypatch):
    """No warnings should be emitted when all advanced params are at default values."""
    engine = _import_engine(monkeypatch)
    feedback = MagicMock()

    _run_with_params(
        engine, monkeypatch, feedback,
        bel_enabled=False,
        clutter_percentile=50.0,
        tx_clutter_override=None,
    )

    assert feedback.pushWarning.call_count == 0, (
        "No pushWarning calls expected with default params, "
        f"got: {feedback.pushWarning.call_args_list}"
    )
