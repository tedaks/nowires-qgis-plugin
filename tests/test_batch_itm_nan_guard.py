# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
from unittest.mock import patch, MagicMock

import numpy as np


def _make_params():
    from NoWires.batch.analysis_params import BatchAnalysisParams
    mock_elev = MagicMock()
    mock_elev.grid = np.zeros((5, 5), dtype=np.float32)
    mock_elev.terrain_profile.return_value = [(0.0, 10.0), (100.0, 12.0)]
    params = BatchAnalysisParams()
    params.elev = mock_elev
    return params


def _make_tx_def():
    return dict(lat=14.5, lon=121.0, height=10.0)


def _make_rx_def():
    return dict(lat=14.501, lon=121.001, height=2.0)


def test_compute_single_link_returns_none_on_failed_itm():
    from NoWires.batch.outputs import _compute_single_link
    mock_itm = MagicMock()
    mock_itm.loss_db = float("nan")
    mock_itm.failed = True
    mock_itm.mode = 0
    mock_itm.warnings = 0
    params = _make_params()
    with patch("NoWires.batch.outputs.itm_p2p_loss", return_value=mock_itm):
        result = _compute_single_link(_make_tx_def(), _make_rx_def(), params, 0.333)
    assert result is None


def test_compute_single_link_returns_none_on_nan_loss():
    from NoWires.batch.outputs import _compute_single_link
    mock_itm = MagicMock()
    mock_itm.loss_db = float("nan")
    mock_itm.failed = False
    mock_itm.mode = 0
    mock_itm.warnings = 0
    params = _make_params()
    with patch("NoWires.batch.outputs.itm_p2p_loss", return_value=mock_itm):
        result = _compute_single_link(_make_tx_def(), _make_rx_def(), params, 0.333)
    assert result is None


def test_compute_single_link_returns_none_on_inf_loss():
    from NoWires.batch.outputs import _compute_single_link
    mock_itm = MagicMock()
    mock_itm.loss_db = float("inf")
    mock_itm.failed = False
    mock_itm.mode = 0
    mock_itm.warnings = 0
    params = _make_params()
    with patch("NoWires.batch.outputs.itm_p2p_loss", return_value=mock_itm):
        result = _compute_single_link(_make_tx_def(), _make_rx_def(), params, 0.333)
    assert result is None