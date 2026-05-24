# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from NoWires.clutter.advanced import (
    ClutterComponents,
    compute_path_clutter_loss,
    compute_terminal_clutter_loss,
)
from NoWires.clutter.categories import CLUTTER_CATEGORY_PARAMS, worldcover_class_to_advanced_category
from NoWires.clutter.context import ClutterLossContext
from NoWires.clutter.saalos import MAX_CLUTTER_LOSS, clutter_loss_saalos


def _make_context(model="simple", distance_m=1000.0, frequency_mhz=900.0,
                  tx_height_m=30.0, rx_height_m=2.0, cch_override_m=None):
    return ClutterLossContext(
        frequency_mhz=frequency_mhz,
        distance_m=distance_m,
        tx_height_m=tx_height_m,
        rx_height_m=rx_height_m,
        rx_ground_elevation_m=0.0,
        tx_ground_elevation_m=0.0,
        polarization=0,
        cch_override_m=cch_override_m,
        model=model,
        percentile=50.0,
        street_width_m=27.0,
        bel_enabled=False,
        bel_building_type="traditional",
        bel_elevation_angle_deg=0.0,
    )


# ---------------------------------------------------------------------------
# clutter/saalos.py line 109 — tvsr > 1000 branch
# ---------------------------------------------------------------------------


def test_saalos_tvsr_over_1000_branch():
    result = clutter_loss_saalos(
        d__meter=15000.0,
        cch__meter=10.0,
        h_tx__meter=2000.0,
        h_rx__meter=1.5,
        h_rx_gnd__meter=0.0,
        pol=0,
        f__mhz=1000.0,
    )
    assert result == pytest.approx(0.243641920562219, rel=1e-9)


# ---------------------------------------------------------------------------
# clutter/saalos.py line 135 — NaN guard in below-canopy path
# ---------------------------------------------------------------------------


def test_saalos_nan_guard_below_canopy_returns_max_clutter_loss():
    result = clutter_loss_saalos(
        d__meter=float("nan"),
        cch__meter=50.0,
        h_tx__meter=1.0,
        h_rx__meter=1.5,
        h_rx_gnd__meter=0.0,
        pol=0,
        f__mhz=1000.0,
    )
    assert result == pytest.approx(MAX_CLUTTER_LOSS, abs=0.01)


# ---------------------------------------------------------------------------
# clutter/categories.py lines 94-95 — invalid class ID → "open"
# ---------------------------------------------------------------------------


def test_worldcover_class_none_returns_open():
    assert worldcover_class_to_advanced_category(None) == "open"


def test_worldcover_class_non_numeric_string_returns_open():
    assert worldcover_class_to_advanced_category("abc") == "open"


def test_worldcover_class_unmapped_numeric_returns_open():
    assert worldcover_class_to_advanced_category("999") == "open"


# ---------------------------------------------------------------------------
# clutter/advanced.py line 139 — unknown model fallback returns 0.0
# ---------------------------------------------------------------------------


def test_compute_terminal_clutter_loss_unknown_model_returns_zero(monkeypatch):
    monkeypatch.setitem(
        CLUTTER_CATEGORY_PARAMS, "fake_cat",
        {"height_m": 5.0, "R_m": 10, "model": "nonexistent_model"},
    )
    ctx = _make_context(model="advanced", distance_m=1000.0)
    result = compute_terminal_clutter_loss("fake_cat", "tx", ctx)
    assert result == 0.0


# ---------------------------------------------------------------------------
# clutter/advanced.py lines 196-201 — dual-saalos zero attribution
# ---------------------------------------------------------------------------


def test_dual_saalos_zero_loss_attribution():
    tx_comp = ClutterComponents(
        terminal_loss_db=0.0, path_loss_db=0.0, model="saalos",
    )
    rx_comp = ClutterComponents(
        terminal_loss_db=0.0, path_loss_db=0.0, model="saalos",
    )
    result = compute_path_clutter_loss(tx_comp, rx_comp)
    assert result == 0.0


def test_dual_saalos_asymmetric_loss():
    tx_comp = ClutterComponents(
        terminal_loss_db=5.0, path_loss_db=0.0, model="saalos",
    )
    rx_comp = ClutterComponents(
        terminal_loss_db=3.0, path_loss_db=0.0, model="saalos",
    )
    result = compute_path_clutter_loss(tx_comp, rx_comp)
    assert result == pytest.approx(5.0, abs=0.01)
