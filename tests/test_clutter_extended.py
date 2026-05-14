# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Extended behavioral tests for clutter.py — clutter_override_value, nodata, context manager."""

import numpy as np
import pytest

from clutter import (
    LandCoverGrid,
    clutter_override_value,
    compute_terminal_clutter_losses,
    CLUTTER_OVERRIDE_OPTIONS,
)


class TestClutterOverrideValue:
    def test_none_returns_none(self):
        assert clutter_override_value(None) is None

    def test_auto_string_returns_none(self):
        assert clutter_override_value("Auto") is None

    def test_valid_category_string_returns_itself(self):
        for cat in ("open", "rural", "vegetation", "suburban", "urban"):
            assert clutter_override_value(cat) == cat

    def test_index_0_auto_returns_none(self):
        # Index 0 is the "Auto" UI option; it must map to None so that
        # downstream category resolution falls back to WorldCover sampling.
        assert clutter_override_value(0) is None

    def test_index_1_returns_open(self):
        assert clutter_override_value(1) == "open"

    def test_index_2_returns_rural(self):
        assert clutter_override_value(2) == "rural"

    def test_index_maps_to_override_options(self):
        for idx in range(1, len(CLUTTER_OVERRIDE_OPTIONS)):
            assert clutter_override_value(idx) == CLUTTER_OVERRIDE_OPTIONS[idx]

    def test_out_of_range_returns_none(self):
        assert clutter_override_value(len(CLUTTER_OVERRIDE_OPTIONS) + 10) is None

    def test_negative_index_returns_none(self):
        assert clutter_override_value(-1) is None

    def test_unknown_string_returns_category(self):
        result = clutter_override_value("unknown_category")
        assert result == "unknown_category"


class TestLandCoverGridNoData:
    def _make_grid_with_nodata(self):
        data = np.array([[10, 50], [80, 255]], dtype=np.int16)
        return LandCoverGrid(
            data=data,
            min_lat=0.0,
            max_lat=1.0,
            min_lon=0.0,
            max_lon=1.0,
            nodata=255.0,
            source="test",
        )

    def test_nodata_pixel_returns_none_class(self):
        grid = self._make_grid_with_nodata()
        result = grid.sample_class(0.25, 0.75)
        assert result is None

    def test_known_class_returns_value(self):
        grid = self._make_grid_with_nodata()
        assert grid.sample_class(0.75, 0.25) == 10

    def test_nodata_with_none_nodata_value(self):
        grid = LandCoverGrid(
            data=np.array([[10, 50]], dtype=np.int16),
            min_lat=0.0, max_lat=0.001,
            min_lon=0.0, max_lon=1.0,
            nodata=None,
            source="test",
        )
        assert grid.sample_class(0.0005, 0.0) == 10
        assert grid.sample_class(0.0005, 1.0) == 50


class TestLandCoverGridContextManager:
    def test_context_manager_releases_data(self):
        grid = LandCoverGrid(
            data=np.array([[10]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        assert grid.data is not None
        with grid as eg:
            assert eg is grid
            assert eg.data is not None
        assert grid.data is None

    def test_close_releases_data(self):
        grid = LandCoverGrid(
            data=np.array([[10]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        grid.close()
        assert grid.data is None

    def test_sampling_after_close_raises_runtime_error(self):
        grid = LandCoverGrid(
            data=np.array([[50]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        grid.close()
        with pytest.raises(RuntimeError, match="closed"):
            grid.sample_class(0.5, 0.5)

    def test_sampling_after_close_grid_raises_runtime_error(self):
        grid = LandCoverGrid(
            data=np.array([[50]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        grid.close()
        with pytest.raises(RuntimeError, match="closed"):
            grid.sample_category_grid(
                np.array([0.5]), np.array([0.5]))


class TestComputeTerminalClutterLossesDisabled:
    def test_disabled_returns_zero_losses(self):
        result = compute_terminal_clutter_losses(
            tx_lat=14.0, tx_lon=121.0,
            rx_lat=14.1, rx_lon=121.1,
            frequency_mhz=900.0,
            enabled=False,
            land_cover_grid=None,
            tx_override=None, rx_override=None,
        )
        assert result.tx_category == "open"
        assert result.rx_category == "open"
        assert result.tx_loss_db == 0.0
        assert result.rx_loss_db == 0.0
        assert result.total_loss_db == 0.0
        assert result.source == "off"


class TestLandCoverGridVectorizedAdvanced:
    def test_advanced_grid_returns_category_strings(self):
        from clutter_context import ClutterLossContext
        grid = LandCoverGrid(
            data=np.array([[50, 10], [80, 20]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        ctx = ClutterLossContext(
            frequency_mhz=1000.0, distance_m=1000.0,
            tx_height_m=30.0, rx_height_m=2.0, model="advanced",
        )
        lats = np.array([0.75, 0.25])
        lons = np.array([0.25, 0.75])
        cats = grid.sample_category_grid(lats, lons, context=ctx)
        assert cats.dtype == object
        assert cats[0, 0] == "urban"
        assert cats[0, 1] == "vegetation"
        assert cats[1, 0] == "open"
        assert cats[1, 1] == "dense_rural"

    def test_advanced_grid_override_broadcasts(self):
        from clutter_context import ClutterLossContext
        grid = LandCoverGrid(
            data=np.array([[50, 50]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        ctx = ClutterLossContext(
            frequency_mhz=1000.0, distance_m=1000.0,
            tx_height_m=30.0, rx_height_m=2.0, model="advanced",
        )
        lats = np.array([0.5])
        lons = np.array([0.25, 0.75])
        cats = grid.sample_category_grid(lats, lons, rx_override="vegetation", context=ctx)
        assert cats[0, 0] == "vegetation"
        assert cats[0, 1] == "vegetation"

    def test_simple_grid_matches_advanced_for_consistent_classes(self):
        grid = LandCoverGrid(
            data=np.array([[50, 60], [10, 80]], dtype=np.int16),
            min_lat=0.0, max_lat=1.0,
            min_lon=0.0, max_lon=1.0,
            nodata=None, source="test",
        )
        lats = np.array([0.75, 0.25])
        lons = np.array([0.25, 0.75])
        simple = grid.sample_category_grid(lats, lons)
        assert simple.shape == (2, 2)
        assert simple.dtype == np.float64
        assert simple[0, 0] == 10.0
        assert simple[0, 1] == 0.0
        assert simple[1, 0] == 6.0
        assert simple[1, 1] == 0.0