# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""End-to-end, property, and performance tests for advanced clutter pipeline."""

import time

import numpy as np

from clutter import (
    LandCoverGrid,
    compute_terminal_clutter_loss,
    compute_terminal_clutter_losses,
)
from clutter.context import ClutterLossContext
from clutter.p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat


def test_advanced_per_pixel_distance_reaches_terrestrial_stat(monkeypatch):
    seen = []

    real = clutter_loss_p2108_terrestrial_stat

    def spy(d_km, f_ghz, p=50.0):
        seen.append(d_km)
        return real(d_km, f_ghz, p)

    monkeypatch.setattr(
        "NoWires.clutter.advanced.clutter_loss_p2108_terrestrial_stat", spy
    )

    grid = LandCoverGrid(
        data=np.full((4, 4), 50, dtype=np.int16),
        min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0,
        nodata=None, source="memory",
    )
    for d in (250.0, 1000.0, 5000.0):
        ctx = ClutterLossContext(
            frequency_mhz=1800.0, distance_m=d,
            tx_height_m=30.0, rx_height_m=2.0, model="advanced",
        )
        compute_terminal_clutter_losses(
            tx_lat=0.5, tx_lon=0.5, rx_lat=0.5, rx_lon=0.5,
            frequency_mhz=1800.0, enabled=True, land_cover_grid=grid,
            context=ctx,
        )
    assert len(seen) > 0


def test_advanced_loss_monotone_in_distance_for_p2108_categories():
    for cat in ("open_rural", "dense_rural", "suburban", "urban"):
        prev = -1.0
        for d in (100.0, 250.0, 500.0, 1000.0, 5000.0, 10_000.0):
            v = compute_terminal_clutter_loss(cat, "rx", ClutterLossContext(
                frequency_mhz=1800.0, distance_m=d,
                tx_height_m=30.0, rx_height_m=2.0, model="advanced",
            ))
            assert v >= prev - 1e-9, f"{cat} non-monotone at d={d}: {v} < {prev}"
            prev = v


def test_advanced_loss_monotone_non_increasing_in_rx_height_for_vegetation():
    prev = float("inf")
    for h in (0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 11.5):
        v = compute_terminal_clutter_loss("vegetation", "rx", ClutterLossContext(
            frequency_mhz=1800.0, distance_m=200.0,
            tx_height_m=30.0, rx_height_m=h, model="advanced",
        ))
        assert v <= prev + 1e-9
        prev = v


def test_disabled_returns_zero_in_advanced_mode():
    ctx = ClutterLossContext(
        frequency_mhz=900.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0, model="advanced",
    )
    r = compute_terminal_clutter_losses(
        tx_lat=0.0, tx_lon=0.0, rx_lat=0.01, rx_lon=0.01,
        frequency_mhz=900.0, enabled=False, context=ctx,
    )
    assert r.total_loss_db == 0.0


def test_terminal_split_preserves_total_invariant_urban_pair():
    """tx_loss + rx_loss must equal total_loss across all advanced cases.

    Previously the §3.2-dominant path left the residual unaccounted for
    in the per-terminal split, producing tx_loss + rx_loss < total.
    """
    grid = LandCoverGrid(
        data=np.full((4, 4), 50, dtype=np.int16),
        min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0,
        nodata=None, source="memory",
    )
    for d_m in (1000.0, 3000.0, 10_000.0):
        for f_mhz in (900.0, 1800.0, 3500.0):
            ctx = ClutterLossContext(
                frequency_mhz=f_mhz, distance_m=d_m,
                tx_height_m=5.0, rx_height_m=1.5, model="advanced",
            )
            r = compute_terminal_clutter_losses(
                tx_lat=0.5, tx_lon=0.5, rx_lat=0.5, rx_lon=0.5,
                frequency_mhz=f_mhz, enabled=True, land_cover_grid=grid,
                context=ctx,
            )
            assert abs(r.tx_loss_db + r.rx_loss_db - r.total_loss_db) < 1e-6, (
                f"split invariant violated: f={f_mhz} d={d_m} "
                f"tx={r.tx_loss_db} rx={r.rx_loss_db} total={r.total_loss_db}"
            )


def test_advanced_per_pixel_is_bounded_for_small_grid():
    start = time.perf_counter()
    for d in range(1, 626):
        compute_terminal_clutter_loss(
            "vegetation", "rx",
            ClutterLossContext(
                frequency_mhz=1800.0, distance_m=float(d),
                tx_height_m=30.0, rx_height_m=2.0, model="advanced",
            ),
        )
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"p833 hot path slower than expected: {elapsed:.2f}s"