# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Tests for clutter_advanced pure-logic functions."""

from unittest.mock import MagicMock, patch

from clutter.advanced import (
    ClutterComponents,
    _category_height_m,
    compute_advanced_loss,
    _terminal_height_m,
    compute_terminal_clutter_loss,
    compute_path_clutter_loss,
)
from clutter.resolve import (
    _resolve_category,
    resolve_category_advanced,
)
from clutter.categories import legacy_to_advanced_override
from clutter.categories import CLUTTER_CATEGORY_PARAMS
from clutter.context import ClutterLossContext


def _ctx(**overrides):
    base = dict(
        frequency_mhz=1000.0,
        distance_m=1000.0,
        tx_height_m=30.0,
        rx_height_m=2.0,
        model="advanced",
    )
    base.update(overrides)
    return ClutterLossContext(**base)


class TestCategoryHeightM:
    def test_override_positive_uses_override(self):
        assert _category_height_m("urban", 20.0) == 20.0

    def test_override_none_falls_back_to_category(self):
        assert _category_height_m("urban", None) == 15.0

    def test_override_zero_uses_zero(self):
        assert _category_height_m("urban", 0.0) == 0.0

    def test_override_negative_falls_back(self):
        assert _category_height_m("urban", -5.0) == 15.0

    def test_unknown_category_falls_back_to_open(self):
        assert _category_height_m("nonexistent_category", None) == CLUTTER_CATEGORY_PARAMS["open"]["height_m"]

    def test_unknown_category_override_positive_still_used(self):
        assert _category_height_m("nonexistent_category", 7.5) == 7.5

    def test_open_category_has_zero_height(self):
        assert _category_height_m("open", None) == 0.0


class TestTerminalHeightM:
    def test_tx_returns_tx_height(self):
        ctx = _ctx(tx_height_m=25.0, rx_height_m=5.0)
        assert _terminal_height_m("tx", ctx) == 25.0

    def test_rx_returns_rx_height(self):
        ctx = _ctx(tx_height_m=25.0, rx_height_m=5.0)
        assert _terminal_height_m("rx", ctx) == 5.0


class TestComputeAdvancedLoss:
    def test_model_none_returns_zero(self):
        ctx = _ctx()
        comp = compute_advanced_loss("open", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "none"

    def test_category_open_returns_zero(self):
        ctx = _ctx()
        comp = compute_advanced_loss("open", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "none"

    def test_cch_override_zero_uses_zero_canopy(self):
        ctx = _ctx(cch_override_m=0.0)
        comp = compute_advanced_loss("urban", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "none"

    def test_cch_override_negative_falls_back_to_category_height(self):
        ctx = _ctx(cch_override_m=-5.0)
        comp = compute_advanced_loss("urban", "rx", ctx)
        assert comp.terminal_loss_db > 0.0 or comp.path_loss_db > 0.0
        assert comp.model != "none"

    def test_open_category_cch_zero_returns_zero(self):
        ctx = _ctx(rx_height_m=0.0)
        comp = compute_advanced_loss("open", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "none"

    def test_antenna_at_clutter_height_returns_zero(self):
        ctx = _ctx(rx_height_m=15.0)
        comp = compute_advanced_loss("urban", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "p2108_combined"

    def test_antenna_above_clutter_height_returns_zero(self):
        ctx = _ctx(rx_height_m=20.0)
        comp = compute_advanced_loss("urban", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "p2108_combined"

    @patch("clutter.advanced.clutter_loss_p833", return_value=8.5)
    def test_model_p833_calls_p833(self, mock_p833):
        ctx = _ctx(frequency_mhz=900.0)
        comp = compute_advanced_loss("vegetation", "rx", ctx)
        assert comp.terminal_loss_db == 8.5
        assert comp.path_loss_db == 0.0
        assert comp.model == "p833"
        mock_p833.assert_called_once()

    @patch("clutter.advanced.height_gain_loss", return_value=3.2)
    def test_model_p2108_height_gain_calls_height_gain(self, mock_hg):
        ctx = _ctx(frequency_mhz=1000.0, rx_height_m=1.0)
        comp = compute_advanced_loss("open_rural", "rx", ctx)
        assert comp.terminal_loss_db == 3.2
        assert comp.path_loss_db == 0.0
        assert comp.model == "p2108_height_gain"
        mock_hg.assert_called_once()

    @patch("clutter.advanced.clutter_loss_p2108_terrestrial_stat", return_value=5.0)
    @patch("clutter.advanced.height_gain_loss", return_value=3.0)
    def test_p2108_combined_mid_band_dispatches_hg_and_stat(self, mock_hg, mock_stat):
        ctx = _ctx(frequency_mhz=1500.0)
        comp = compute_advanced_loss("suburban", "rx", ctx)
        assert comp.terminal_loss_db == 3.0
        assert comp.path_loss_db == 5.0
        assert "§3.1" in comp.model
        assert "§3.2" in comp.model

    @patch("clutter.advanced.clutter_loss_p2108_terrestrial_stat", return_value=5.0)
    @patch("clutter.advanced.height_gain_loss", return_value=0.0)
    def test_p2108_combined_mid_band_hg_zero_skips_31(self, mock_hg, mock_stat):
        ctx = _ctx(frequency_mhz=1500.0)
        comp = compute_advanced_loss("suburban", "rx", ctx)
        assert "§3.1" not in comp.model
        assert "§3.2" in comp.model
        assert comp.path_loss_db == 5.0

    @patch("clutter.advanced.clutter_loss_p2108_terrestrial_stat", return_value=0.0)
    @patch("clutter.advanced.height_gain_loss", return_value=0.0)
    def test_p2108_combined_mid_band_both_zero_returns_zero(self, mock_hg, mock_stat):
        ctx = _ctx(frequency_mhz=1500.0)
        comp = compute_advanced_loss("suburban", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "p2108_combined(0)"

    @patch("clutter.advanced.clutter_loss_p2108_terrestrial_stat", return_value=6.0)
    def test_p2108_combined_high_band_uses_stat_only(self, mock_stat):
        ctx = _ctx(frequency_mhz=10000.0)
        comp = compute_advanced_loss("urban", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 6.0
        assert comp.model == "§3.2"

    @patch("clutter.advanced.clutter_loss_p2108_terrestrial_stat", return_value=4.0)
    def test_p2108_combined_very_high_band_clamps_frequency(self, mock_stat):
        ctx = _ctx(frequency_mhz=100000.0)
        comp = compute_advanced_loss("urban", "rx", ctx)
        assert comp.path_loss_db == 4.0
        assert "3.2" in comp.model
        assert "clamped" in comp.model

    def test_p2108_combined_low_band_warns_once(self, caplog):
        import logging as _logging
        # Reset the module-level latch so this test is independent of order.
        import clutter.resolve as clutter_resolve
        clutter_resolve._STATE.warned_low_vhf = False
        with caplog.at_level(_logging.WARNING, logger="clutter_advanced"):
            compute_advanced_loss("urban", "rx", _ctx(frequency_mhz=47.0))
            compute_advanced_loss("suburban", "rx", _ctx(frequency_mhz=47.0))
        # Exactly one warning even after two below-band calls.
        warns = [r for r in caplog.records if "P.2108 §3.2 invalid below" in r.getMessage()]
        assert len(warns) == 1

    def test_p2108_combined_low_band_no_loss(self):
        ctx = _ctx(frequency_mhz=400.0)
        comp = compute_advanced_loss("suburban", "rx", ctx)
        assert comp.terminal_loss_db == 0.0
        assert comp.path_loss_db == 0.0
        assert comp.model == "p2108_combined(0)"

    @patch("clutter.advanced.height_gain_loss", return_value=2.0)
    def test_p2108_combined_s32_not_applicable(self, mock_hg):
        ctx = _ctx(frequency_mhz=1500.0, rx_height_m=1.0)
        comp = compute_advanced_loss("open_rural", "rx", ctx)
        assert comp.terminal_loss_db == 2.0
        assert comp.path_loss_db == 0.0
        assert "§3.2" not in comp.model

    def test_unknown_model_returns_zero_unknown(self):
        with patch.dict(
            "clutter.categories.CLUTTER_CATEGORY_PARAMS",
            {"fake_cat": {"height_m": 10.0, "model": "bad_model", "p2108_3_2_applicable": False}},
        ):
            ctx = _ctx(rx_height_m=2.0)
            comp = compute_advanced_loss("fake_cat", "rx", ctx)
            assert comp.terminal_loss_db == 0.0
            assert comp.path_loss_db == 0.0
            assert comp.model == "unknown"


class TestComputeTerminalClutterLoss:
    @patch("clutter.advanced.compute_advanced_loss",
           return_value=ClutterComponents(5.0, 2.5, "p2108_combined"))
    def test_delegates_tocompute_advanced_loss_for_p2108(self, mock_adv):
        ctx = _ctx()
        result = compute_terminal_clutter_loss("suburban", "rx", ctx)
        assert result == 5.0
        mock_adv.assert_called_once_with("suburban", "rx", ctx)

    def test_model_none_returns_zero(self):
        ctx = _ctx()
        assert compute_terminal_clutter_loss("open", "rx", ctx) == 0.0

    def test_distance_zero_returns_zero(self):
        ctx = _ctx(distance_m=0.0)
        assert compute_terminal_clutter_loss("urban", "rx", ctx) == 0.0

    def test_distance_negative_returns_zero(self):
        ctx = _ctx(distance_m=-100.0)
        assert compute_terminal_clutter_loss("urban", "rx", ctx) == 0.0

    @patch("clutter.advanced.clutter_loss_p833", return_value=5.0)
    def test_p833_model_delegates_to_compute_advanced_loss(self, mock_p833):
        ctx = _ctx(frequency_mhz=900.0)
        result = compute_terminal_clutter_loss("vegetation", "rx", ctx)
        assert result == 5.0
        mock_p833.assert_called_once()


class TestComputePathClutterLoss:
    def test_both_none_returns_zero(self):
        tx = ClutterComponents(0.0, 0.0, "none")
        rx = ClutterComponents(0.0, 0.0, "none")
        assert compute_path_clutter_loss(tx, rx) == 0.0

    def test_p2108_height_gain_additive(self):
        tx = ClutterComponents(3.0, 0.0, "p2108_height_gain")
        rx = ClutterComponents(2.0, 0.0, "p2108_height_gain")
        assert compute_path_clutter_loss(tx, rx) == 5.0

    def test_p2108_combined_stat_not_double_counted(self):
        tx = ClutterComponents(2.0, 10.0, "§3.1+§3.2")
        rx = ClutterComponents(3.0, 10.0, "§3.1+§3.2")
        result = compute_path_clutter_loss(tx, rx)
        assert result == 10.0, "§3.2 path loss should be counted once, not summed"

    def test_p2108_combined_hg_sum_dominates(self):
        tx = ClutterComponents(8.0, 10.0, "§3.1+§3.2")
        rx = ClutterComponents(7.0, 10.0, "§3.1+§3.2")
        result = compute_path_clutter_loss(tx, rx)
        assert result == 15.0, "when hg_tx+hg_rx > stat, use hg sum"

    def test_p2108_combined_mixed_height_gain_only(self):
        tx = ClutterComponents(3.0, 0.0, "p2108_height_gain")
        rx = ClutterComponents(0.0, 10.0, "§3.2")
        result = compute_path_clutter_loss(tx, rx)
        assert result == max(3.0, 10.0) == 10.0

    def test_p833_both_endpoints_sums(self):
        tx = ClutterComponents(18.0, 0.0, "p833")
        rx = ClutterComponents(12.0, 0.0, "p833")
        result = compute_path_clutter_loss(tx, rx)
        assert result == 30.0, "P.833 terminal losses are independent; sum both"

    def test_one_endpoint_none(self):
        tx = ClutterComponents(0.0, 0.0, "none")
        rx = ClutterComponents(3.0, 0.0, "p2108_height_gain")
        assert compute_path_clutter_loss(tx, rx) == 3.0

    def test_stat_path_dominates(self):
        tx = ClutterComponents(1.0, 20.0, "§3.1+§3.2")
        rx = ClutterComponents(1.0, 20.0, "§3.1+§3.2")
        result = compute_path_clutter_loss(tx, rx)
        assert result == 20.0

    def test_path_stat_takes_max_not_sum(self):
        tx = ClutterComponents(0.0, 15.0, "§3.2")
        rx = ClutterComponents(0.0, 15.0, "§3.2")
        result = compute_path_clutter_loss(tx, rx)
        assert result == 15.0, "path stat should be max of both, not sum"


class TestLegacyToAdvancedOverride:
    def test_open_maps_to_open(self):
        assert legacy_to_advanced_override("open") == "open"

    def test_rural_maps_to_open_rural(self):
        assert legacy_to_advanced_override("rural") == "open_rural"

    def test_vegetation_maps_to_vegetation(self):
        assert legacy_to_advanced_override("vegetation") == "vegetation"

    def test_suburban_maps_to_suburban(self):
        assert legacy_to_advanced_override("suburban") == "suburban"

    def test_urban_maps_to_urban(self):
        assert legacy_to_advanced_override("urban") == "urban"

    def test_open_rural_idempotent(self):
        assert legacy_to_advanced_override("open_rural") == "open_rural"

    def test_dense_rural_idempotent(self):
        assert legacy_to_advanced_override("dense_rural") == "dense_rural"

    def test_unknown_name_returns_open(self):
        assert legacy_to_advanced_override("unknown_cat") == "open"


class TestResolveCategoryAdvanced:
    def test_override_provided_returns_mapping(self):
        result = resolve_category_advanced(0.0, 0.0, "urban", None)
        assert result == ("urban", "override")

    def test_override_rural_maps_to_open_rural(self):
        result = resolve_category_advanced(0.0, 0.0, "rural", None)
        assert result == ("open_rural", "override")

    def test_no_override_no_grid_returns_fallback(self):
        result = resolve_category_advanced(0.0, 0.0, None, None)
        assert result == ("open", "fallback_open")

    def test_grid_with_class_returns_advanced_category(self):
        grid = MagicMock()
        grid.sample_class.return_value = 50
        result = resolve_category_advanced(14.0, 121.0, None, grid)
        assert result[0] == "urban"
        assert result[1] == grid.source
        grid.sample_class.assert_called_once_with(14.0, 121.0)

    def test_grid_returns_none_class_falls_back(self):
        grid = MagicMock()
        grid.sample_class.return_value = None
        result = resolve_category_advanced(14.0, 121.0, None, grid)
        assert result == ("open", "fallback_open")

    def test_override_takes_precedence_over_grid(self):
        grid = MagicMock()
        result = resolve_category_advanced(14.0, 121.0, "vegetation", grid)
        assert result == ("vegetation", "override")
        grid.sample_class.assert_not_called()


class TestResolveCategory:
    def test_override_provided_returns_override(self):
        result = _resolve_category(0.0, 0.0, "urban", None)
        assert result == ("urban", "override")

    def test_no_override_no_grid_returns_fallback(self):
        result = _resolve_category(0.0, 0.0, None, None)
        assert result == ("open", "fallback_open")

    def test_grid_with_category_returns_category(self):
        grid = MagicMock()
        grid.sample_category.return_value = "urban"
        result = _resolve_category(14.0, 121.0, None, grid)
        assert result[0] == "urban"
        assert result[1] == grid.source
        grid.sample_category.assert_called_once_with(14.0, 121.0)

    def test_grid_returns_none_category_falls_back(self):
        grid = MagicMock()
        grid.sample_category.return_value = None
        result = _resolve_category(14.0, 121.0, None, grid)
        assert result == ("open", "fallback_open")

    def test_override_takes_precedence_over_grid(self):
        grid = MagicMock()
        result = _resolve_category(14.0, 121.0, "suburban", grid)
        assert result == ("suburban", "override")
        grid.sample_category.assert_not_called()