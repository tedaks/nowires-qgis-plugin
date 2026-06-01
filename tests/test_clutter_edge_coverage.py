# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

import pytest

from NoWires.clutter.advanced import (
    ClutterComponents,
    compute_path_clutter_loss,
    compute_terminal_clutter_loss,
)
from NoWires.clutter.categories import CLUTTER_CATEGORY_PARAMS, worldcover_class_to_advanced_category
from NoWires.clutter.context import ClutterLossContext


def _make_context(model="simple", distance_m=1000.0, frequency_mhz=900.0,
                  tx_height_m=30.0, rx_height_m=2.0, cch_override_m=None):
    return ClutterLossContext(
        frequency_mhz=frequency_mhz,
        distance_m=distance_m,
        tx_height_m=tx_height_m,
        rx_height_m=rx_height_m,
        cch_override_m=cch_override_m,
        model=model,
        percentile=50.0,
        street_width_m=27.0,
        bel_enabled=False,
        bel_building_type="traditional",
        bel_elevation_angle_deg=0.0,
    )


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
# compute_path_clutter_loss — p833 dual-endpoint behaviour
# ---------------------------------------------------------------------------


def test_dual_p833_zero_loss_returns_zero():
    tx_comp = ClutterComponents(terminal_loss_db=0.0, path_loss_db=0.0, model="p833")
    rx_comp = ClutterComponents(terminal_loss_db=0.0, path_loss_db=0.0, model="p833")
    result = compute_path_clutter_loss(tx_comp, rx_comp)
    assert result == 0.0


def test_dual_p833_sums_both_terminals():
    tx_comp = ClutterComponents(terminal_loss_db=5.0, path_loss_db=0.0, model="p833")
    rx_comp = ClutterComponents(terminal_loss_db=3.0, path_loss_db=0.0, model="p833")
    result = compute_path_clutter_loss(tx_comp, rx_comp)
    assert result == pytest.approx(8.0, abs=0.01)
