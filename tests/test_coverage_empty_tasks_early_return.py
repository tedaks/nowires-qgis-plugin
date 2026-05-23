# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np
from unittest.mock import MagicMock


def test_compute_coverage_returns_none_on_empty_tasks():
    from NoWires.radio_coverage.engine import compute_coverage
    mock_elev = MagicMock()
    mock_elev.grid = np.zeros((5, 5), dtype=np.float32)
    mock_elev.sample = MagicMock(return_value=10.0)
    mock_elev.grid_meta_dict = MagicMock(return_value={})
    result = compute_coverage(
        tx_lat=14.5, tx_lon=121.0, tx_h_m=10.0, rx_h_m=2.0,
        f_mhz=900.0, tx_power_dbm=43.0, tx_gain_dbi=0.0,
        rx_gain_dbi=0.0, cable_loss_db=0.0, rx_sensitivity_dbm=-100.0,
        radius_km=0.0, grid_size=2,
        elev_grid=mock_elev, clutter_enabled=False, feedback=MagicMock(),
    )
    assert result is None