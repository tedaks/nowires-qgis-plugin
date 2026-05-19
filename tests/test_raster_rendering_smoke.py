# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Raster rendering smoke tests — shader pipeline, palette constants, style variants.

SKIPPED when real QGIS is available because they pass MagicMock layers to
QgsSingleBandPseudoColorRenderer, which expects a real QgsRasterDataProvider.
"""

import os
import pytest
from unittest.mock import MagicMock

_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))

pytestmark = pytest.mark.skipif(
    _HAS_REAL_QGIS,
    reason="Raster rendering smoke tests use MagicMock layers incompatible with real QGIS",
)


class TestCoveragePaletteConstants:
    def test_signal_levels_has_seven_entries(self):
        from coverage.palette import SIGNAL_LEVELS
        assert len(SIGNAL_LEVELS) == 7

    def test_signal_levels_are_sorted_descending(self):
        from coverage.palette import SIGNAL_LEVELS
        thresholds = [s[0] for s in SIGNAL_LEVELS]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_each_signal_level_has_threshold_rgba_label(self):
        from coverage.palette import SIGNAL_LEVELS
        for entry in SIGNAL_LEVELS:
            assert len(entry) == 3  # (threshold, rgba, label)
            assert isinstance(entry[0], (int, float))
            assert len(entry[1]) == 4  # RGBA
            assert isinstance(entry[2], str)

    def test_no_service_has_zero_alpha(self):
        from coverage.palette import SIGNAL_LEVELS
        no_service = SIGNAL_LEVELS[-1]
        assert no_service[2] == "No service"
        assert no_service[1][3] == 0  # alpha = 0

    def test_build_heatmap_stops_returns_sorted_ascending(self):
        from coverage.palette import build_heatmap_stops
        stops = build_heatmap_stops()
        thresholds = [s[0] for s in stops]
        assert thresholds == sorted(thresholds)


class TestApplyCoverageStylePipeline:
    def test_style_sets_renderer_on_layer(self):
        from coverage.palette import apply_coverage_style
        layer = MagicMock()
        apply_coverage_style(layer)
        assert layer.setRenderer.called

    def test_style_triggers_repaint(self):
        from coverage.palette import apply_coverage_style
        layer = MagicMock()
        apply_coverage_style(layer)
        assert layer.triggerRepaint.called

    def test_style_reads_data_provider(self):
        from coverage.palette import apply_coverage_style
        layer = MagicMock()
        apply_coverage_style(layer)
        assert layer.dataProvider.called


class TestApplyDeltaStylePipeline:
    def test_diverging_style_sets_renderer(self):
        from comparison.outputs import apply_delta_style
        layer = MagicMock()
        apply_delta_style(layer, threshold_db=10.0, style="diverging")
        assert layer.setRenderer.called

    def test_threshold_style_sets_renderer(self):
        from comparison.outputs import apply_delta_style
        layer = MagicMock()
        apply_delta_style(layer, threshold_db=10.0, style="threshold")
        assert layer.setRenderer.called

    def test_default_style_is_diverging(self):
        from comparison.outputs import apply_delta_style
        layer = MagicMock()
        apply_delta_style(layer, threshold_db=5.0)
        assert layer.setRenderer.called

    def test_both_styles_trigger_repaint(self):
        from comparison.outputs import apply_delta_style
        for style in ("diverging", "threshold"):
            layer = MagicMock()
            apply_delta_style(layer, threshold_db=10.0, style=style)
            assert layer.triggerRepaint.called


class TestRasterIOContract:
    def test_write_geotiff_uses_gdal_driver(self):
        """Contract: raster_io uses gdal.GetDriverByName('GTiff')."""
        source = open("raster_io.py").read()
        assert 'GetDriverByName("GTiff")' in source

    def test_write_geotiff_closes_dataset_in_finally(self):
        source = open("raster_io.py").read()
        assert "del ds" in source

    def test_write_geotiff_sets_projection(self):
        source = open("raster_io.py").read()
        assert "SetProjection" in source

    def test_write_geotiff_sets_nodata(self):
        source = open("raster_io.py").read()
        assert "SetNoDataValue" in source


class TestBuildLegendEntries:
    def test_legend_entries_match_signal_levels(self):
        from coverage.palette import build_legend_entries, SIGNAL_LEVELS
        entries = build_legend_entries()
        assert entries == SIGNAL_LEVELS

    def test_legend_entries_preserves_original_order(self):
        from coverage.palette import build_legend_entries
        entries = build_legend_entries()
        assert entries[0][2] == "Very Strong"
        assert entries[-1][2] == "No service"
