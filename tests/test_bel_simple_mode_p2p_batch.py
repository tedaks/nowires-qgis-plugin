# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: BEL must be computed in simple-clutter mode for P2P/Batch."""

from NoWires.clutter.advanced import compute_terminal_clutter_losses
from NoWires.clutter.context import ClutterLossContext


def test_simple_mode_bel_populated_when_enabled():
    """Simple-mode BEL must produce non-zero total_with_bel_db when BEL enabled."""
    ctx = ClutterLossContext(
        frequency_mhz=900.0,
        distance_m=5000.0,
        tx_height_m=30.0,
        rx_height_m=10.0,
        model="simple",
        bel_enabled=True,
        bel_building_type="traditional",
        bel_elevation_angle_deg=0.0,
        percentile=50.0,
    )
    result = compute_terminal_clutter_losses(
        tx_lat=0.0, tx_lon=0.0, rx_lat=0.01, rx_lon=0.01,
        frequency_mhz=900.0, enabled=True, context=ctx,
    )
    assert result.total_with_bel_db > result.total_loss_db, (
        "total_with_bel_db ({}) must exceed total_loss_db ({}) when BEL enabled in simple mode"
        .format(result.total_with_bel_db, result.total_loss_db)
    )
    assert result.rx_bel_db > 0.0, (
        "rx_bel_db must be > 0 when BEL is enabled"
    )


def test_simple_mode_bel_zero_when_disabled():
    """Simple-mode BEL must be zero when bel_enabled=False."""
    ctx = ClutterLossContext(
        frequency_mhz=900.0,
        distance_m=5000.0,
        tx_height_m=30.0,
        rx_height_m=10.0,
        model="simple",
        bel_enabled=False,
        bel_building_type="traditional",
        bel_elevation_angle_deg=0.0,
        percentile=50.0,
    )
    result = compute_terminal_clutter_losses(
        tx_lat=0.0, tx_lon=0.0, rx_lat=0.01, rx_lon=0.01,
        frequency_mhz=900.0, enabled=True, context=ctx,
    )
    assert result.rx_bel_db == 0.0
    assert result.total_with_bel_db == result.total_loss_db