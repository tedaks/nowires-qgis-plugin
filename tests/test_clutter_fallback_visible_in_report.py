# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: clutter report must surface fallback as unavailable."""

from NoWires.radio_coverage.reporting import _clutter_model_label


class TestClutterFallbackVisibleInReport:
    def test_fallback_open_appends_unavailable_suffix(self):
        label = _clutter_model_label(
            enabled=True, model="simple", clutter_source="fallback_open",
        )
        assert "unavailable" in label.lower()

    def test_normal_source_leaves_label_unchanged(self):
        label = _clutter_model_label(
            enabled=True, model="simple", clutter_source="/path/to/raster.tif",
        )
        assert "/path/to/raster.tif" not in label
        assert "Simple" in label

    def test_off_model_ignores_fallback_source(self):
        label = _clutter_model_label(
            enabled=False, model="simple", clutter_source="fallback_open",
        )
        assert label == "Off"

    def test_advanced_fallback_still_shows_advanced_label_with_suffix(self):
        label = _clutter_model_label(
            enabled=True, model="advanced", clutter_source="fallback_open",
        )
        assert "Advanced" in label
        assert "unavailable" in label.lower()

    def test_coverage_report_builder_passes_clutter_source(self):
        import os
        source_path = os.path.join(
            os.path.dirname(__file__), "..", "radio_coverage", "reporting.py",
        )
        with open(source_path, encoding="utf-8") as f:
            source = f.read()
        assert "clutter_source" in source
        assert "_clutter_model_label(params.clutter_enabled, params.clutter_model, clutter_source)" in source
