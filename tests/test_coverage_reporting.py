# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for coverage report/raster generation helpers."""

from types import SimpleNamespace

import numpy as np

from NoWires.coverage.reporting import (
    build_coverage_report_payload_for_grid,
    report_coverage_results,
    write_coverage_geotiff,
)


def _tx_clutter(loss=0.0):
    return SimpleNamespace(tx_loss_db=loss)


def _base_payload_kwargs():
    return {
        "tx_lat": 1.75,
        "tx_lon": 0.5,
        "tx_h": 30.0,
        "rx_h": 10.0,
        "f_mhz": 900.0,
        "radius_km": 1.0,
        "grid_size": 2,
        "polarization": 1,
        "climate": 1,
        "time_pct": 50.0,
        "location_pct": 50.0,
        "situation_pct": 50.0,
        "tx_power": 43.0,
        "tx_gain": 8.0,
        "rx_gain": 2.0,
        "cable_loss": 2.0,
        "rx_sens": -100.0,
        "clutter_enabled": True,
        "antenna_preset": 0,
        "clutter_source": "memory",
        "tx_clutter_for_report": _tx_clutter(2.0),
    }


def test_build_coverage_report_payload_flips_grid_for_raster_summary():
    prx_grid = np.array(
        [
            [-130.0, -130.0],
            [-95.0, -130.0],
        ],
        dtype=np.float32,
    )
    loss_grid = np.array(
        [
            [np.nan, np.nan],
            [122.0, np.nan],
        ],
        dtype=np.float32,
    )
    itm_loss_grid = np.array(
        [
            [np.nan, np.nan],
            [115.0, np.nan],
        ],
        dtype=np.float32,
    )
    clutter_loss_grid = np.array(
        [
            [np.nan, np.nan],
            [7.0, np.nan],
        ],
        dtype=np.float32,
    )
    clutter_rx_db_grid = np.array(
        [
            [np.nan, np.nan],
            [5.0, np.nan],
        ],
        dtype=np.float32,
    )
    bel_rx_db_grid = np.array(
        [
            [np.nan, np.nan],
            [0.0, np.nan],
        ],
        dtype=np.float32,
    )

    payload, raster_grid, valid, summary = build_coverage_report_payload_for_grid(
        prx_grid=prx_grid,
        loss_grid=loss_grid,
        itm_loss_grid=itm_loss_grid,
        clutter_loss_grid=clutter_loss_grid,
        clutter_rx_db_grid=clutter_rx_db_grid,
        bel_rx_db_grid=bel_rx_db_grid,
        min_lat=0.0,
        max_lat=2.0,
        min_lon=0.0,
        max_lon=1.0,
        **_base_payload_kwargs(),
    )

    assert raster_grid.tolist() == [[-95.0, -130.0], [-130.0, -130.0]]
    assert valid.tolist() == [[True, True], [True, True]]
    assert summary["usable_cell_count"] == 1
    assert payload["results"]["valid_pixel_count"] == 4
    assert payload["results"]["pct_above_sensitivity"] == 25.0
    assert payload["results"]["itm_loss_db"] == 115.0
    assert payload["results"]["clutter_tx_db"] == 2.0
    assert payload["results"]["clutter_rx_db"] == 5.0
    assert payload["results"]["bel_rx_db"] == 0.0
    assert payload["results"]["total_path_loss_db"] == 122.0


def test_build_coverage_report_payload_handles_all_nan_grid():
    prx_grid = np.full((2, 2), np.nan, dtype=np.float32)

    payload, raster_grid, valid, summary = build_coverage_report_payload_for_grid(
        prx_grid=prx_grid,
        loss_grid=prx_grid.copy(),
        itm_loss_grid=prx_grid.copy(),
        clutter_loss_grid=prx_grid.copy(),
        clutter_rx_db_grid=prx_grid.copy(),
        bel_rx_db_grid=prx_grid.copy(),
        min_lat=0.0,
        max_lat=2.0,
        min_lon=0.0,
        max_lon=1.0,
        **_base_payload_kwargs(),
    )

    assert summary is None
    assert not valid.any()
    assert np.isnan(raster_grid).all()
    assert payload["results"]["valid_pixel_count"] == 0
    assert payload["results"]["clutter_tx_db"] == 2.0
    assert payload["status"]["summary"] == "NO VALID COVERAGE CELLS"


def test_build_coverage_report_payload_labels_advanced_clutter():
    prx_grid = np.array([[-95.0]], dtype=np.float32)
    loss_grid = np.array([[122.0]], dtype=np.float32)
    itm_loss_grid = np.array([[115.0]], dtype=np.float32)
    clutter_loss_grid = np.array([[7.0]], dtype=np.float32)
    clutter_rx_db_grid = np.array([[5.0]], dtype=np.float32)

    payload, _raster_grid, _valid, _summary = build_coverage_report_payload_for_grid(
        prx_grid=prx_grid,
        loss_grid=loss_grid,
        itm_loss_grid=itm_loss_grid,
        clutter_loss_grid=clutter_loss_grid,
        clutter_rx_db_grid=clutter_rx_db_grid,
        bel_rx_db_grid=np.array([[0.0]], dtype=np.float32),
        min_lat=0.0,
        max_lat=1.0,
        min_lon=0.0,
        max_lon=1.0,
        clutter_model="advanced",
        **_base_payload_kwargs(),
    )

    assert payload["inputs"]["clutter_model"] == "Advanced clutter correction"


def test_write_coverage_geotiff_delegates_raw_compute_grid(monkeypatch, tmp_path):
    import NoWires.coverage.reporting as module

    calls = []
    prx_grid = np.array([[1.0], [2.0]], dtype=np.float32)

    monkeypatch.setattr(module, "write_geotiff", lambda *args: calls.append(args))

    write_coverage_geotiff(
        prx_grid,
        min_lat=0.0,
        max_lat=2.0,
        min_lon=10.0,
        max_lon=11.0,
        tif_path=str(tmp_path / "coverage.tif"),
    )

    assert calls == [
        (str(tmp_path / "coverage.tif"), prx_grid, 0.0, 2.0, 10.0, 11.0)
    ]


def test_report_coverage_results_includes_no_service_message():
    class Feedback:
        def __init__(self):
            self.messages = []

        def pushInfo(self, message):
            self.messages.append(message)

    feedback = Feedback()
    payload = {
        "results": {
            "availability_method": "heuristic_availability",
            "reliability_summary": "Marginal",
            "fade_margin_class": "thin",
            "availability_estimate_pct": None,
        }
    }

    report_coverage_results(
        feedback=feedback,
        report_payload=payload,
        raster_grid=np.array([[-120.0]], dtype=np.float32),
        valid=np.array([[True]]),
        rx_sens=-100.0,
        summary={
            "usable_cell_count": 0,
            "min_distance_km": 0.0,
            "max_distance_km": 0.0,
            "average_distance_km": 0.0,
        },
    )

    assert "No cells met the RX sensitivity threshold." in feedback.messages
