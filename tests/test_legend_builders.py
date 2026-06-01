# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for coverage legend data builders."""

import os

from NoWires.radio_coverage.palette import build_legend_entries


class TestBuildLegendEntries:
    def test_returns_all_signal_levels(self):
        entries = build_legend_entries()
        assert len(entries) == 7

    def test_each_entry_has_threshold_rgba_label(self):
        for entry in build_legend_entries():
            assert len(entry) == 3
            threshold, rgba, label = entry
            assert isinstance(threshold, float)
            assert len(rgba) == 4
            assert isinstance(label, str)

    def test_entries_are_in_descending_threshold_order(self):
        entries = build_legend_entries()
        thresholds = [e[0] for e in entries]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_last_entry_is_no_service(self):
        entries = build_legend_entries()
        assert entries[-1][2] == "No service"

    def test_first_entry_is_very_strong(self):
        entries = build_legend_entries()
        assert entries[0][2] == "Very Strong"


class TestLegendSourceContract:
    def test_legend_module_uses_build_legend_entries(self):
        source_path = os.path.join(
            os.path.dirname(__file__), "..", "radio_coverage", "legend.py",
        )
        with open(source_path, encoding="utf-8") as f:
            source = f.read()
        assert "from NoWires.radio_coverage.palette import build_legend_entries" in source
        assert "build_legend_entries()" in source

    def test_legend_has_cleanup_method(self):
        source_path = os.path.join(
            os.path.dirname(__file__), "..", "radio_coverage", "legend.py",
        )
        with open(source_path, encoding="utf-8") as f:
            source = f.read()
        assert "class CoverageLegendWidget" in source
        assert "def cleanup(self)" in source
