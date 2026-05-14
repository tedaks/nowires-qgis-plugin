# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for coverage_engine.py — helper functions and edge paths."""

import numpy as np

from NoWires.coverage_engine import (
    _get_tx_ground_elevation,
    _build_rx_ground_grid,
    _build_clutter_context,
    _compute_tx_clutter_loss,
)
from NoWires.clutter_context import ClutterLossContext


class _ElevObj:
    def sample(self, lat, lon):
        return 100.0


class _ElevObjNaN:
    def sample(self, lat, lon):
        return float("nan")


class _GridObj:
    def sample_grid(self, lats, lons):
        grid = np.array([
            [10.0, 20.0, 30.0],
            [40.0, 50.0, 60.0],
            [70.0, 80.0, 90.0],
        ], dtype=np.float32)
        return grid

    def sample(self, lat, lon):
        return 50.0


class TestGetTXGroundElevation:
    def test_sample_returns_finite_value(self):
        elev = _ElevObj()
        result = _get_tx_ground_elevation(elev, 0.0, 0.0)
        assert result == 100.0

    def test_nan_elevation_returns_zero(self):
        elev = _ElevObjNaN()
        result = _get_tx_ground_elevation(elev, 0.0, 0.0)
        assert result == 0.0

    def test_no_sample_method_returns_zero(self):
        elev = object()
        result = _get_tx_ground_elevation(elev, 0.0, 0.0)
        assert result == 0.0


class TestBuildRXGroundGrid:
    def test_clutter_disabled_returns_none(self):
        result = _build_rx_ground_grid(
            _GridObj(), False, "simple", np.array([0.0]), np.array([0.0]), 1,
        )
        assert result is None

    def test_simple_model_returns_none(self):
        result = _build_rx_ground_grid(
            _GridObj(), True, "simple", np.array([0.0]), np.array([0.0]), 1,
        )
        assert result is None

    def test_advanced_model_with_sample_grid(self):
        result = _build_rx_ground_grid(
            _GridObj(), True, "advanced",
            np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0]), 3,
        )
        assert result is not None
        assert result.shape == (3, 3)
        assert result.dtype == np.float32

    def test_advanced_model_fallback_to_sample(self):
        class _Samplable:
            def sample(self, lat, lon):
                return 42.0

        result = _build_rx_ground_grid(
            _Samplable(), True, "advanced",
            np.array([0.0, 1.0]), np.array([0.0, 1.0]), 2,
        )
        assert result is not None
        assert result.shape == (2, 2)

    def test_advanced_model_no_method_returns_none(self):
        elev = object()
        result = _build_rx_ground_grid(
            elev, True, "advanced", np.array([0.0]), np.array([0.0]), 1,
        )
        assert result is None


class TestBuildClutterContext:
    def test_disabled_returns_passed_context(self):
        ctx = object()
        result = _build_clutter_context(
            False, ctx, 900.0, 30.0, 10.0, 0.0, 0, None, "simple",
            50.0, 27.0, False, "traditional", 0.0,
        )
        assert result is ctx

    def test_existing_context_returned_as_is(self):
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=0.0,
            tx_height_m=30.0, rx_height_m=10.0, model="simple",
        )
        result = _build_clutter_context(
            True, ctx, 900.0, 30.0, 10.0, 0.0, 0, None, "simple",
            50.0, 27.0, False, "traditional", 0.0,
        )
        assert result is ctx

    def test_enabled_no_context_creates_new(self):
        result = _build_clutter_context(
            True, None, 900.0, 30.0, 10.0, 25.0, 0, None, "simple",
            50.0, 27.0, False, "traditional", 0.0,
        )
        assert isinstance(result, ClutterLossContext)
        assert result.model == "simple"
        assert result.tx_ground_elevation_m == 25.0

    def test_enabled_advanced_context(self):
        result = _build_clutter_context(
            True, None, 900.0, 30.0, 10.0, 25.0, 1, 5.0, "advanced",
            90.0, 30.0, True, "thermally_efficient", 10.0,
        )
        assert result.model == "advanced"
        assert result.bel_enabled is True
        assert result.bel_building_type == "thermally_efficient"


class TestComputeTXClutterLoss:
    def test_preset_loss_returned(self):
        result = _compute_tx_clutter_loss(
            0.0, 0.0, 5.0, 900.0, False, None, None, None, None,
        )
        assert result == 5.0

    def test_advanced_model_skips_precompute(self):
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=0.0,
            tx_height_m=30.0, rx_height_m=10.0, model="advanced",
        )
        result = _compute_tx_clutter_loss(
            0.0, 0.0, None, 900.0, True, None, None, None, ctx,
        )
        assert result == 0.0

    def test_simple_model_computes(self):
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=0.0,
            tx_height_m=30.0, rx_height_m=10.0, model="simple",
        )
        result = _compute_tx_clutter_loss(
            0.0, 0.0, None, 900.0, True, None, None, None, ctx,
        )
        assert isinstance(result, float)
