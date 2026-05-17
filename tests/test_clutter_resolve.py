# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for clutter_resolve pure-logic functions."""

from unittest.mock import MagicMock

from clutter_resolve import (
    _maybe_warn_low_vhf_p2108_combined,
    _resolve_category,
    resolve_category_advanced,
)
from clutter_categories import legacy_to_advanced_override


class TestMaybeWarnLowVhfP2108Combined:
    def test_emits_warning_on_first_call(self, caplog):
        import clutter_resolve
        clutter_resolve._STATE.warned_low_vhf = False
        import logging
        with caplog.at_level(logging.WARNING, logger="clutter_resolve"):
            _maybe_warn_low_vhf_p2108_combined(0.3, "urban")
        warns = [r for r in caplog.records if "P.2108" in r.getMessage()]
        assert len(warns) == 1

    def test_suppresses_warning_on_second_call(self, caplog):
        import clutter_resolve
        clutter_resolve._STATE.warned_low_vhf = False
        import logging
        with caplog.at_level(logging.WARNING, logger="clutter_resolve"):
            _maybe_warn_low_vhf_p2108_combined(0.3, "urban")
            _maybe_warn_low_vhf_p2108_combined(0.4, "suburban")
        warns = [r for r in caplog.records if "P.2108" in r.getMessage()]
        assert len(warns) == 1

    def test_resets_after_manual_reset(self, caplog):
        import clutter_resolve
        clutter_resolve._STATE.warned_low_vhf = False
        import logging
        with caplog.at_level(logging.WARNING, logger="clutter_resolve"):
            _maybe_warn_low_vhf_p2108_combined(0.3, "urban")
        clutter_resolve._STATE.warned_low_vhf = False
        with caplog.at_level(logging.WARNING, logger="clutter_resolve"):
            _maybe_warn_low_vhf_p2108_combined(0.3, "suburban")
        warns = [r for r in caplog.records if "P.2108" in r.getMessage()]
        assert len(warns) == 2

    def test_returns_early_without_warning_when_latch_set(self, caplog):
        import clutter_resolve
        clutter_resolve._STATE.warned_low_vhf = True
        import logging
        with caplog.at_level(logging.WARNING, logger="clutter_resolve"):
            _maybe_warn_low_vhf_p2108_combined(0.3, "urban")
        warns = [r for r in caplog.records if "P.2108" in r.getMessage()]
        assert len(warns) == 0


class TestLegacyToAdvancedOverride:
    def test_open_maps_to_open(self):
        assert legacy_to_advanced_override("open") == "open"

    def test_rural_maps_to_open_rural(self):
        assert legacy_to_advanced_override("rural") == "open_rural"

    def test_vegetation_idempotent(self):
        assert legacy_to_advanced_override("vegetation") == "vegetation"

    def test_suburban_idempotent(self):
        assert legacy_to_advanced_override("suburban") == "suburban"

    def test_urban_idempotent(self):
        assert legacy_to_advanced_override("urban") == "urban"

    def test_unknown_returns_open(self):
        assert legacy_to_advanced_override("nonexistent") == "open"


class TestResolveCategoryAdvanced:
    def test_override_provieded_returns_override(self):
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