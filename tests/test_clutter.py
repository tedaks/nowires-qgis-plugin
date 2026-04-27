# -*- coding: utf-8 -*-
"""Behavioral tests for clutter correction helpers."""

import numpy as np
import pytest

from clutter import (
    CLUTTER_LOSS_DB,
    LandCoverGrid,
    clutter_loss_db,
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