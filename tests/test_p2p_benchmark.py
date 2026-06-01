# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Pytest configuration for benchmarks."""

from __future__ import annotations

import time
import importlib

import pytest


def test_p2p_benchmark_module_exists():
    module = importlib.import_module("NoWires.benchmarks.p2p_runtime")
    assert hasattr(module, "run_case")


def test_run_p2p_case_reports_elapsed_and_loss(monkeypatch):
    monkeypatch.setattr(time, "perf_counter", iter([10.0, 10.05]).__next__)

    module = importlib.import_module("NoWires.benchmarks.p2p_runtime")
    importlib.reload(module)

    calls = {}

    def fake_compute_itm_p2p(**kwargs):
        calls["kwargs"] = kwargs
        return {
            "itm_loss_db": 120.0,
            "clutter_tx_db": 0.0,
            "clutter_rx_db": 0.0,
            "total_path_loss_db": 120.0,
            "antenna_gain_adjustment_db": 0.0,
            "received_power_dbm": -90.0,
        }

    monkeypatch.setattr(module, "compute_itm_p2p", fake_compute_itm_p2p)

    case = module.P2PCase(
        label="smoke",
        distance_km=1.0,
        terrain="flat",
        frequency_mhz=900.0,
    )
    result = module.run_case(case)

    assert calls["kwargs"]["f__mhz"] == 900.0
    assert result["label"] == "smoke"
    assert result["distance_km"] == 1.0
    assert result["loss_db"] == 120.0
    assert result["elapsed_s"] == 0.05


@pytest.mark.benchmark
def test_p2p_small_rural_case_loads():
    module = importlib.import_module("NoWires.benchmarks.p2p_runtime")
    case = next(c for c in module.P2P_CASES if c.label == "short_rural")
    assert case.distance_km == 1.0
    assert case.terrain == "flat"


@pytest.mark.benchmark
def test_p2p_medium_urban_case_loads():
    module = importlib.import_module("NoWires.benchmarks.p2p_runtime")
    case = next(c for c in module.P2P_CASES if c.label == "medium_urban")
    assert case.distance_km == 5.0
    assert case.terrain == "varied"


@pytest.mark.benchmark
def test_p2p_long_los_case_loads():
    module = importlib.import_module("NoWires.benchmarks.p2p_runtime")
    case = next(c for c in module.P2P_CASES if c.label == "long_los")
    assert case.distance_km == 20.0
    assert case.terrain == "coastal"
