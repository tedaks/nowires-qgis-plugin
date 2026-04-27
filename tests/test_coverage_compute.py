# -*- coding: utf-8 -*-
"""Regression tests for coverage compute helpers."""

import importlib
from types import SimpleNamespace

import numpy as np


def test_compute_module_exists():
    module = importlib.import_module("NoWires.coverage_compute")
    assert hasattr(module, "compute_itm_p2p")


def test_compute_itm_p2p_uses_radio_bridge(monkeypatch):
    module = importlib.import_module("NoWires.coverage_compute")

    calls = {}

    def fake_build_pfl(elevations, step_m):
        calls["pfl"] = (elevations, step_m)
        return ["pfl"]

    def fake_itm_p2p_loss(**kwargs):
        calls["itm"] = kwargs
        return SimpleNamespace(loss_db=144.5)

    monkeypatch.setattr(module, "build_pfl", fake_build_pfl)
    monkeypatch.setattr(module, "itm_p2p_loss", fake_itm_p2p_loss)

    result = module.compute_itm_p2p(
        h_tx__meter=30.0,
        h_rx__meter=10.0,
        elevations=np.array([100.0, 101.0, 102.0]),
        resolution=50.0,
        climate_idx=1,
        N_0=301.0,
        f__mhz=300.0,
        polarization=0,
        epsilon=15.0,
        sigma=0.005,
        time_pct=50.0,
        location_pct=50.0,
        situation_pct=50.0,
        eirp_dbm=43.0,
        ant_gain_adj=3.0,
        rx_gain_dbi=2.0,
        clutter_tx_db=2.0,
        clutter_rx_db=6.0,
    )

    assert calls["pfl"] == ([100.0, 101.0, 102.0], 50.0)
    assert calls["itm"]["profile"] == ["pfl"]
    assert result == {
        "itm_loss_db": 144.5,
        "clutter_tx_db": 2.0,
        "clutter_rx_db": 6.0,
        "total_path_loss_db": 152.5,
        "antenna_gain_adjustment_db": 3.0,
        "received_power_dbm": -104.5,
    }
