# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for coverage_engine.py — helper functions and edge paths."""

from NoWires.radio_coverage.engine import (
    _build_clutter_context,
    _compute_tx_clutter_loss,
)
from NoWires.clutter.context import ClutterLossContext


class TestBuildClutterContext:
    def test_disabled_returns_passed_context(self):
        ctx = object()
        result = _build_clutter_context(
            False, ctx, 900.0, 30.0, 10.0, None, "simple",
            50.0, 27.0, False, "traditional", 0.0,
        )
        assert result is ctx

    def test_existing_context_returned_as_is(self):
        ctx = ClutterLossContext(
            frequency_mhz=900.0, distance_m=0.0,
            tx_height_m=30.0, rx_height_m=10.0, model="simple",
        )
        result = _build_clutter_context(
            True, ctx, 900.0, 30.0, 10.0, None, "simple",
            50.0, 27.0, False, "traditional", 0.0,
        )
        assert result is ctx

    def test_enabled_no_context_creates_new(self):
        result = _build_clutter_context(
            True, None, 900.0, 30.0, 10.0, None, "simple",
            50.0, 27.0, False, "traditional", 0.0,
        )
        assert isinstance(result, ClutterLossContext)
        assert result.model == "simple"

    def test_enabled_advanced_context(self):
        result = _build_clutter_context(
            True, None, 900.0, 30.0, 10.0, 5.0, "advanced",
            90.0, 30.0, True, "thermally_efficient", 10.0,
        )
        assert result.model == "advanced"
        assert result.bel_enabled is True
        assert result.bel_building_type == "thermally_efficient"

    def test_bel_only_no_clutter_creates_simple_context(self):
        result = _build_clutter_context(
            False, None, 900.0, 30.0, 10.0, None, "simple",
            50.0, 27.0, True, "traditional", 0.0,
        )
        assert isinstance(result, ClutterLossContext)
        assert result.model == "simple"
        assert result.bel_enabled is True


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
