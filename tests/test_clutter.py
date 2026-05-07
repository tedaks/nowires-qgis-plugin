# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for clutter correction helpers."""

import os
import tempfile

import numpy as np

from clutter import (
    CLUTTER_LOSS_DB,
    CLUTTER_MODEL_OPTIONS,
    CLUTTER_OVERRIDE_OPTIONS,
    LEGACY_CLUTTER_CATEGORIES,
    LandCoverGrid,
    clutter_loss_db,
    clutter_source_label,
    compute_terminal_clutter_losses,
    worldcover_class_to_clutter_category,
)


def test_worldcover_classes_map_to_clutter_categories():
    assert worldcover_class_to_clutter_category(10) == "vegetation"
    assert worldcover_class_to_clutter_category(30) == "rural"
    assert worldcover_class_to_clutter_category(50) == "urban"
    assert worldcover_class_to_clutter_category(80) == "open"
    assert worldcover_class_to_clutter_category(999) == "open"


def test_initial_loss_table_matches_todo_values():
    assert CLUTTER_LOSS_DB == {
        "open": 0.0,
        "rural": 2.0,
        "vegetation": 6.0,
        "suburban": 8.0,
        "urban": 10.0,
    }
    assert clutter_loss_db("urban", 900.0) == 10.0


_TMP_WORLDCOVER = os.path.join(tempfile.gettempdir(), "worldcover.tif")


def test_land_cover_grid_samples_nearest_class():
    grid = LandCoverGrid(
        data=np.array([[10, 30], [50, 80]], dtype=np.int16),
        min_lat=0.0,
        max_lat=1.0,
        min_lon=0.0,
        max_lon=1.0,
        nodata=None,
        source="memory",
    )

    assert grid.sample_class(0.75, 0.25) == 10
    assert grid.sample_category(0.25, 0.25) == "urban"
    assert grid.sample_category(5.0, 5.0) is None


def test_land_cover_grid_vectorized_sampling_falls_back_for_unknown_class():
    grid = LandCoverGrid(
        data=np.array([[999]], dtype=np.int16),
        min_lat=0.0,
        max_lat=1.0,
        min_lon=0.0,
        max_lon=1.0,
        nodata=None,
        source="memory",
    )

    losses = grid.sample_category_grid(np.array([0.5]), np.array([0.5]))

    assert losses.tolist() == [[0.0]]


def test_compute_terminal_clutter_losses_uses_overrides_before_raster():
    grid = LandCoverGrid(
        data=np.array([[50, 50], [50, 50]], dtype=np.int16),
        min_lat=0.0,
        max_lat=1.0,
        min_lon=0.0,
        max_lon=1.0,
        nodata=None,
        source="memory",
    )

    result = compute_terminal_clutter_losses(
        tx_lat=0.5,
        tx_lon=0.5,
        rx_lat=0.5,
        rx_lon=0.5,
        frequency_mhz=900.0,
        enabled=True,
        land_cover_grid=grid,
        tx_override="open",
        rx_override=None,
    )

    assert result.tx_category == "open"
    assert result.rx_category == "urban"
    assert result.tx_loss_db == 0.0
    assert result.rx_loss_db == 10.0
    assert result.total_loss_db == 10.0


def test_ensure_clutter_grid_for_area_returns_none_when_download_disabled(monkeypatch):
    import worldcover_downloader as wd

    monkeypatch.setattr(wd, "ensure_worldcover_for_area", lambda *a, **kw: None)

    from clutter import ensure_clutter_grid_for_area

    result = ensure_clutter_grid_for_area(0, 1, 0, 1)
    assert result is None


def test_clutter_source_label_reports_auto_downloaded_grid_source():
    grid = LandCoverGrid(
        data=np.array([[50]], dtype=np.int16),
        min_lat=0.0,
        max_lat=1.0,
        min_lon=0.0,
        max_lon=1.0,
        nodata=None,
        source=_TMP_WORLDCOVER,
    )

    assert clutter_source_label(
        enabled=True,
        land_cover_grid=grid,
        raster_path=None,
        tx_override=None,
        rx_override=None,
    ) == _TMP_WORLDCOVER
    assert clutter_source_label(
        enabled=True,
        land_cover_grid=grid,
        raster_path=None,
        tx_override="urban",
        rx_override=None,
    ) == "override," + _TMP_WORLDCOVER
    assert clutter_source_label(
        enabled=True,
        land_cover_grid=None,
        raster_path=None,
        tx_override="urban",
        rx_override=None,
    ) == "override"
    assert clutter_source_label(
        enabled=True,
        land_cover_grid=None,
        raster_path=None,
        tx_override=None,
        rx_override=None,
    ) == "fallback_open"


def test_clutter_model_options_order_is_stable():
    assert CLUTTER_MODEL_OPTIONS == [
        "Off",
        "Simple clutter correction",
        "Advanced clutter correction",
    ]


def test_clutter_override_options_legacy_indices_preserved():
    assert CLUTTER_OVERRIDE_OPTIONS[:6] == [
        "Auto", "open", "rural", "vegetation", "suburban", "urban",
    ]
    assert "open_rural" in CLUTTER_OVERRIDE_OPTIONS[6:]
    assert "dense_rural" in CLUTTER_OVERRIDE_OPTIONS[6:]


def test_legacy_categories_unchanged():
    assert LEGACY_CLUTTER_CATEGORIES == (
        "open", "rural", "vegetation", "suburban", "urban",
    )


from clutter import compute_terminal_clutter_loss, _category_height_m
from clutter_context import ClutterLossContext


def _ctx(**overrides):
    base = dict(
        frequency_mhz=1000.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0, model="advanced",
    )
    base.update(overrides)
    return ClutterLossContext(**base)


def test_advanced_helper_returns_zero_for_open():
    assert compute_terminal_clutter_loss("open", "rx", _ctx()) == 0.0


def test_advanced_helper_gates_when_antenna_above_clutter():
    assert compute_terminal_clutter_loss("urban", "rx", _ctx(rx_height_m=30.0)) == 0.0


def test_advanced_helper_uses_tx_height_for_tx_terminal():
    assert compute_terminal_clutter_loss("vegetation", "tx", _ctx(tx_height_m=30.0)) == 0.0


def test_advanced_helper_p2108_for_urban():
    v = compute_terminal_clutter_loss("urban", "rx", _ctx())
    assert v > 0.0


def test_advanced_helper_saalos_for_vegetation():
    v = compute_terminal_clutter_loss("vegetation", "rx", _ctx())
    assert v > 0.0


def test_advanced_helper_zero_distance_zero_loss():
    assert compute_terminal_clutter_loss("urban", "rx", _ctx(distance_m=0.0)) == 0.0


def test_cch_override_applies():
    v_default = compute_terminal_clutter_loss("vegetation", "rx", _ctx())
    v_override = compute_terminal_clutter_loss("vegetation", "rx", _ctx(cch_override_m=25.0))
    assert _category_height_m("vegetation", 25.0) == 25.0
    assert _category_height_m("vegetation", None) == 12.0
    assert v_default > 0.0 and v_override > 0.0


from clutter import TerminalClutterLosses


def test_simple_mode_unchanged_when_context_none():
    grid = LandCoverGrid(
        data=np.array([[50, 50], [50, 50]], dtype=np.int16),
        min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0,
        nodata=None, source="memory",
    )
    result = compute_terminal_clutter_losses(
        tx_lat=0.5, tx_lon=0.5, rx_lat=0.5, rx_lon=0.5,
        frequency_mhz=1000.0, enabled=True, land_cover_grid=grid,
    )
    assert result.tx_category == "urban"
    assert result.tx_loss_db == 10.0
    assert result.rx_loss_db == 10.0


def test_advanced_mode_uses_dispatcher():
    grid = LandCoverGrid(
        data=np.array([[50, 50], [50, 50]], dtype=np.int16),
        min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0,
        nodata=None, source="memory",
    )
    ctx = ClutterLossContext(
        frequency_mhz=1000.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0, model="advanced",
    )
    result = compute_terminal_clutter_losses(
        tx_lat=0.5, tx_lon=0.5, rx_lat=0.5, rx_lon=0.5,
        frequency_mhz=1000.0, enabled=True, land_cover_grid=grid,
        context=ctx,
    )
    assert result.rx_category == "urban"
    assert 0.0 < result.rx_loss_db < 10.0
    assert result.rx_cch_m == 15.0


def test_advanced_disabled_returns_zero():
    ctx = ClutterLossContext(
        frequency_mhz=1000.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0, model="advanced",
    )
    result = compute_terminal_clutter_losses(
        tx_lat=0.0, tx_lon=0.0, rx_lat=0.0, rx_lon=0.0,
        frequency_mhz=1000.0, enabled=False, context=ctx,
    )
    assert result.total_loss_db == 0.0
    assert result.tx_cch_m == 0.0
    assert result.rx_cch_m == 0.0


def test_overrides_take_precedence_in_advanced():
    grid = LandCoverGrid(
        data=np.array([[50, 50], [50, 50]], dtype=np.int16),
        min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0,
        nodata=None, source="memory",
    )
    ctx = ClutterLossContext(
        frequency_mhz=1000.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0, model="advanced",
    )
    result = compute_terminal_clutter_losses(
        tx_lat=0.5, tx_lon=0.5, rx_lat=0.5, rx_lon=0.5,
        frequency_mhz=1000.0, enabled=True, land_cover_grid=grid,
        tx_override="open", rx_override=None, context=ctx,
    )
    assert result.tx_category == "open"
    assert result.tx_loss_db == 0.0
    assert result.rx_category == "urban"
    assert result.rx_loss_db > 0.0


def test_terminal_clutter_losses_dataclass_extension_is_additive():
    legacy = TerminalClutterLosses("open", "open", 0.0, 0.0, 0.0, "off")
    assert legacy.tx_cch_m == 0.0 and legacy.rx_cch_m == 0.0
