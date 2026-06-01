# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Edge case tests for batch/outputs.py _compute_single_link."""

import os
import sys
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "NoWires"))


def _make_params(elev=None):
    from NoWires.batch.analysis_params import BatchAnalysisParams
    params = BatchAnalysisParams()
    params.elev = elev
    return params


def _make_tx_def(**overrides):
    d = dict(lat=14.5, lon=121.0, height=10.0)
    d.update(overrides)
    return d


def _make_rx_def(**overrides):
    d = dict(lat=14.501, lon=121.001, height=2.0)
    d.update(overrides)
    return d


def _make_itm_mock(loss_db=100.0, failed=False):
    mock = MagicMock()
    mock.loss_db = loss_db
    mock.failed = failed
    mock.mode = 0
    mock.warnings = 0
    return mock


def _make_elev_mock(profile_points=None):
    mock = MagicMock()
    mock.terrain_profile.return_value = profile_points or [(0.0, 10.0), (1000.0, 12.0)]
    return mock


class TestComputeSingleLinkEdges:
    def test_distance_less_than_1m_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        params = _make_params(elev=_make_elev_mock())
        tx = _make_tx_def(lat=14.5, lon=121.0)
        rx = _make_rx_def(lat=14.5, lon=121.0)
        result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_no_elev_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        params = _make_params(elev=None)
        tx = _make_tx_def()
        rx = _make_rx_def()
        result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_too_few_profile_points_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock(profile_points=[(0.0, 10.0)])
        params = _make_params(elev=elev)
        tx = _make_tx_def()
        rx = _make_rx_def()
        with patch("NoWires.batch.outputs.itm_p2p_loss") as mock_itm:
            mock_itm.return_value = _make_itm_mock(loss_db=100.0)
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_all_nan_elevations_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock(profile_points=[(0.0, float("nan")), (500.0, float("nan")), (1000.0, float("nan"))])
        params = _make_params(elev=elev)
        tx = _make_tx_def()
        rx = _make_rx_def()
        with patch("NoWires.batch.outputs.itm_p2p_loss") as mock_itm:
            mock_itm.return_value = _make_itm_mock(loss_db=100.0)
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_tx_height_below_itm_min_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock()
        params = _make_params(elev=elev)
        tx = _make_tx_def(height=0.0)
        rx = _make_rx_def()
        with patch("NoWires.radio.ITM_MIN_TERMINAL_HEIGHT_M", 50.0), \
             patch("NoWires.radio.ITM_MAX_TERMINAL_HEIGHT_M", 30000.0):
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_tx_height_above_itm_max_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock()
        params = _make_params(elev=elev)
        tx = _make_tx_def(height=50000.0)
        rx = _make_rx_def()
        with patch("NoWires.radio.ITM_MIN_TERMINAL_HEIGHT_M", 0.3), \
             patch("NoWires.radio.ITM_MAX_TERMINAL_HEIGHT_M", 10000.0):
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_rx_height_below_itm_min_returns_none(self):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock()
        params = _make_params(elev=elev)
        tx = _make_tx_def()
        rx = _make_rx_def(height=0.0)
        with patch("NoWires.radio.ITM_MIN_TERMINAL_HEIGHT_M", 50.0), \
             patch("NoWires.radio.ITM_MAX_TERMINAL_HEIGHT_M", 30000.0):
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is None

    def test_feature_height_overrides_params(self, monkeypatch):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock()
        params = _make_params(elev=elev)
        params.tx_h = 50.0
        params.rx_h = 25.0
        tx = _make_tx_def(height=30.0)
        rx = _make_rx_def(height=5.0)
        with patch("NoWires.batch.outputs.itm_p2p_loss") as mock_itm:
            mock_itm.return_value = _make_itm_mock(loss_db=100.0)
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is not None

    def test_none_feature_height_uses_params(self, monkeypatch):
        from NoWires.batch.outputs import _compute_single_link
        elev = _make_elev_mock()
        params = _make_params(elev=elev)
        params.tx_h = 50.0
        params.rx_h = 25.0
        tx = _make_tx_def(height=None)
        rx = _make_rx_def(height=None)
        with patch("NoWires.batch.outputs.itm_p2p_loss") as mock_itm:
            mock_itm.return_value = _make_itm_mock(loss_db=100.0)
            result = _compute_single_link(tx, rx, params, 0.333)
        assert result is not None
