# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Infrastructure coverage tests for batch outputs, batch writer, and comparison panel.

Covers _compute_single_link edge cases, write_batch_csv NaN handling,
and run_panel_coverage result dispatch.
"""

import csv
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

_EPSILON = 1.0e-9

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthetic_profile(dist_m=1000.0, step_m=30.0, elev_base=10.0, elev_bump=5.0):
    """Return a list of (distance, elevation) tuples simulating a gentle slope."""
    n = max(2, int(dist_m / step_m) + 1)
    pts = []
    for i in range(n):
        d = i * step_m
        e = elev_base + (elev_bump * i / max(n - 1, 1))
        pts.append((d, e))
    return pts


def _make_params_with_elev(profile=None):
    """Create a BatchAnalysisParams with a mocked ElevationGrid."""
    from NoWires.batch.analysis_params import BatchAnalysisParams

    mock_elev = MagicMock()
    mock_elev.terrain_profile.return_value = profile or _synthetic_profile()

    params = BatchAnalysisParams()
    params.elev = mock_elev
    params.total = 1
    return params


def _make_tx_def(lat=14.5, lon=121.0, height=10.0):
    return dict(lat=lat, lon=lon, height=height)


def _make_rx_def(lat=14.501, lon=121.001, height=2.0):
    return dict(lat=lat, lon=lon, height=height)


def _valid_itm_result(loss_db=120.0):
    mock = MagicMock()
    mock.loss_db = float(loss_db)
    mock.failed = False
    mock.mode = 0
    mock.warnings = 0
    return mock


def _valid_coverage_result():
    from NoWires.radio_coverage.pool import CoverageResult

    gs = 100
    nan32 = np.float32(np.nan)
    return CoverageResult(
        prx_grid=np.full((gs, gs), -50.0, dtype=np.float32),
        loss_grid=np.full((gs, gs), 120.0, dtype=np.float32),
        min_lat=44.0, max_lat=45.0, min_lon=10.0, max_lon=11.0,
        itm_loss_grid=np.full((gs, gs), 118.0, dtype=np.float32),
        clutter_loss_grid=np.full((gs, gs), nan32, dtype=np.float32),
        clutter_rx_db_grid=np.full((gs, gs), nan32, dtype=np.float32),
        bel_rx_db_grid=np.full((gs, gs), nan32, dtype=np.float32),
    )


# ---------------------------------------------------------------------------
# batch/outputs.py — _compute_single_link
# ---------------------------------------------------------------------------


def test_compute_single_link_returns_none_on_itm_failure():
    """Synthetic elevation with ITM returning failed=True must yield None."""
    from NoWires.batch.outputs import _compute_single_link

    params = _make_params_with_elev()
    mock_itm = MagicMock()
    mock_itm.loss_db = 120.0
    mock_itm.failed = True

    with patch("NoWires.batch.outputs.itm_p2p_loss", return_value=mock_itm):
        result = _compute_single_link(_make_tx_def(), _make_rx_def(), params, 0.333)
    assert result is None


def test_compute_single_link_returns_none_on_nan_loss():
    """ITM returning NaN loss must yield None (isfinite guard)."""
    from NoWires.batch.outputs import _compute_single_link

    params = _make_params_with_elev()
    mock_itm = MagicMock()
    mock_itm.loss_db = float("nan")
    mock_itm.failed = False

    with patch("NoWires.batch.outputs.itm_p2p_loss", return_value=mock_itm):
        result = _compute_single_link(_make_tx_def(), _make_rx_def(), params, 0.333)
    assert result is None


def test_compute_single_link_returns_result_on_success():
    """Full success path: valid ITM result, valid fresnel analysis, clutter, antenna."""
    from NoWires.batch.outputs import _compute_single_link

    profile = _synthetic_profile(dist_m=1000.0, step_m=100.0, elev_base=10.0, elev_bump=5.0)
    params = _make_params_with_elev(profile=profile)

    mock_itm = _valid_itm_result(loss_db=120.0)
    mock_clutter_losses = MagicMock()
    mock_clutter_losses.total_with_bel_db = 0.0
    n_pts = len(profile)
    mock_fresnel = (
        np.zeros(n_pts),
        np.full(n_pts, 20.0),
        np.full(n_pts, 2.0),
        0,
        0,
        0,
    )
    mock_ant_config = MagicMock()

    with patch("NoWires.batch.outputs.itm_p2p_loss", return_value=mock_itm), \
         patch("NoWires.batch.outputs.compute_terminal_clutter_losses",
               return_value=mock_clutter_losses), \
         patch("NoWires.batch.outputs.fresnel_profile_analysis",
               return_value=mock_fresnel), \
         patch("NoWires.batch.outputs.antenna_config_from_values",
               return_value=mock_ant_config), \
         patch("NoWires.batch.outputs.antenna_gain_adjustment_db",
               return_value=0.0):
        result = _compute_single_link(_make_tx_def(), _make_rx_def(), params, 0.333)

    assert result is not None
    assert isinstance(result, dict)
    assert "tx_lat" in result
    assert "rx_lat" in result
    assert "dist_m" in result
    assert result["dist_m"] > 0.0
    assert "dist_km" in result
    assert abs(result["dist_km"] - result["dist_m"] / 1000.0) < _EPSILON
    assert "itm_loss_db" in result
    assert result["itm_loss_db"] == 120.0
    assert "total_loss_db" in result
    assert "prx_dbm" in result
    assert "margin_db" in result
    assert "clearance_pct" in result
    assert "status" in result
    assert result["status"] in ("VIABLE", "NOT VIABLE")
    assert "tx_height" in result
    assert "rx_height" in result
    assert "climate" in result


# ---------------------------------------------------------------------------
# batch/writer.py — write_batch_csv
# ---------------------------------------------------------------------------

_EXPECTED_HEADERS = [
    "Point Id", "rank", "tx_lat", "tx_lon", "rx_lat", "rx_lon",
    "dist_km", "itm_loss_db", "total_loss_db",
    "margin_db", "clearance_pct", "status", "climate",
]


def test_batch_writer_creates_csv_header(tmp_path):
    """write_batch_csv must emit the expected header row."""
    from NoWires.batch.writer import write_batch_csv

    path = tmp_path / "out.csv"
    write_batch_csv(str(path), [], mode=1)
    with open(str(path), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == _EXPECTED_HEADERS


def test_batch_writer_writes_row_with_nan(tmp_path):
    """NaN values in result fields must be serialized without crashing."""
    from NoWires.batch.writer import write_batch_csv

    nan_row = {
        "tx_lat": 14.0, "tx_lon": 121.0,
        "rx_lat": 14.01, "rx_lon": 121.01,
        "dist_km": float("nan"),
        "itm_loss_db": float("nan"),
        "total_loss_db": 130.0,
        "margin_db": 5.0,
        "clearance_pct": 50.0,
        "status": "VIABLE",
        "climate": "Continental Temperate",
    }
    path = tmp_path / "out.csv"
    write_batch_csv(str(path), [nan_row], mode=1)
    with open(str(path), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2
    dist_km_idx = _EXPECTED_HEADERS.index("dist_km")
    itm_loss_idx = _EXPECTED_HEADERS.index("itm_loss_db")
    assert rows[1][dist_km_idx] == "nan"
    assert rows[1][itm_loss_idx] == "nan"


# ---------------------------------------------------------------------------
# comparison/panel.py — run_panel_coverage
# ---------------------------------------------------------------------------


@pytest.mark.qgis_integration
def test_run_panel_coverage_returns_result():
    """run_panel_coverage must return a dict with a valid CoverageResult."""
    from NoWires.comparison.panel import run_panel_coverage

    valid_result = _valid_coverage_result()
    panel_params = MagicMock()
    panel_params.clutter_enabled = False
    panel_params.clutter_raster_path = None
    panel_params.clutter_model = "simple"
    panel_params.clutter_percentile = 50.0
    panel_params.street_width_m = 27.0
    panel_params.bel_enabled = False
    panel_params.bel_building_type = "traditional"
    panel_params.bel_elevation_angle_deg = 0.0
    panel_params.cch_override_m = None
    panel_params.tx_lat = 44.0
    panel_params.tx_lon = 10.0
    panel_params.tx_h = 30.0
    panel_params.rx_h = 10.0
    panel_params.f_mhz = 900.0
    panel_params.radius_km = 5.0
    panel_params.grid_size = 100
    panel_params.polarization = 1
    panel_params.climate = 1
    panel_params.time_pct = 50.0
    panel_params.location_pct = 50.0
    panel_params.situation_pct = 50.0
    panel_params.tx_power = 43.0
    panel_params.tx_gain = 8.0
    panel_params.rx_gain = 2.0
    panel_params.cable_loss = 2.0
    panel_params.rx_sens = -100.0
    panel_params.antenna_bw = 360.0
    panel_params.antenna_az = None
    panel_params.antenna_preset = 0
    panel_params.front_back_db = 25.0
    panel_params.downtilt_deg = 0.0
    panel_params.h_pattern = ""
    panel_params.v_pattern = ""
    panel_params.tx_clutter_override = None
    panel_params.rx_clutter_override = None
    panel_params.antenna_bw_override = None
    panel_params.n0 = 301.0
    panel_params.epsilon = 15.0
    panel_params.sigma = 0.005

    mock_algo = MagicMock()

    with patch("NoWires.comparison.panel.collect_panel_params", return_value=panel_params), \
         patch("NoWires.comparison.panel.validate_itm_input_ranges"), \
         patch("NoWires.comparison.panel.clutter_source_label", return_value="none"), \
         patch("NoWires.comparison.panel.compute_terminal_clutter_losses") as mock_clutter, \
         patch("NoWires.comparison.panel.compute_coverage", return_value=valid_result):
        mock_clutter_losses = MagicMock()
        mock_clutter_losses.tx_loss_db = 0.0
        mock_clutter.return_value = mock_clutter_losses

        result = run_panel_coverage(
            algorithm_instance=mock_algo,
            prefix="A",
            parameters={},
            context=MagicMock(),
            feedback=MagicMock(),
            elev=MagicMock(),
            south=44.0,
            north=45.0,
            west=10.0,
            east=11.0,
            shared_clutter_grid=None,
        )

    assert isinstance(result, dict)
    assert "result" in result
    assert result["result"] is not None
    assert result["result"] is valid_result
    assert "clutter_source" in result
    assert "tx_clutter_for_report" in result
    assert "clutter_enabled" in result
    assert result["clutter_enabled"] == panel_params.clutter_enabled
    assert "tx_lat" in result
    assert result["tx_lat"] == panel_params.tx_lat
    assert "tx_lon" in result
    assert result["tx_lon"] == panel_params.tx_lon


@pytest.mark.qgis_integration
def test_run_panel_coverage_raises_on_none_result():
    """When compute_coverage returns None the result dict must carry result=None."""
    from NoWires.comparison.panel import run_panel_coverage

    panel_params = MagicMock()
    panel_params.clutter_enabled = False
    panel_params.clutter_raster_path = None
    panel_params.clutter_model = "simple"
    panel_params.clutter_percentile = 50.0
    panel_params.street_width_m = 27.0
    panel_params.bel_enabled = False
    panel_params.bel_building_type = "traditional"
    panel_params.bel_elevation_angle_deg = 0.0
    panel_params.cch_override_m = None
    panel_params.tx_lat = 44.0
    panel_params.tx_lon = 10.0
    panel_params.tx_h = 30.0
    panel_params.rx_h = 10.0
    panel_params.f_mhz = 900.0
    panel_params.radius_km = 5.0
    panel_params.grid_size = 100
    panel_params.polarization = 1
    panel_params.climate = 1
    panel_params.time_pct = 50.0
    panel_params.location_pct = 50.0
    panel_params.situation_pct = 50.0
    panel_params.tx_power = 43.0
    panel_params.tx_gain = 8.0
    panel_params.rx_gain = 2.0
    panel_params.cable_loss = 2.0
    panel_params.rx_sens = -100.0
    panel_params.antenna_bw = 360.0
    panel_params.antenna_az = None
    panel_params.antenna_preset = 0
    panel_params.front_back_db = 25.0
    panel_params.downtilt_deg = 0.0
    panel_params.h_pattern = ""
    panel_params.v_pattern = ""
    panel_params.tx_clutter_override = None
    panel_params.rx_clutter_override = None
    panel_params.antenna_bw_override = None
    panel_params.n0 = 301.0
    panel_params.epsilon = 15.0
    panel_params.sigma = 0.005

    with patch("NoWires.comparison.panel.collect_panel_params", return_value=panel_params), \
         patch("NoWires.comparison.panel.validate_itm_input_ranges"), \
         patch("NoWires.comparison.panel.clutter_source_label", return_value="none"), \
         patch("NoWires.comparison.panel.compute_terminal_clutter_losses") as mock_clutter, \
         patch("NoWires.comparison.panel.compute_coverage", return_value=None):
        mock_clutter_losses = MagicMock()
        mock_clutter_losses.tx_loss_db = 0.0
        mock_clutter.return_value = mock_clutter_losses

        result = run_panel_coverage(
            algorithm_instance=MagicMock(),
            prefix="A",
            parameters={},
            context=MagicMock(),
            feedback=MagicMock(),
            elev=MagicMock(),
            south=44.0,
            north=45.0,
            west=10.0,
            east=11.0,
            shared_clutter_grid=None,
        )

    assert isinstance(result, dict)
    assert "result" in result
    assert result["result"] is None
