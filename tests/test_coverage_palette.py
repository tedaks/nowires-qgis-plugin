# -*- coding: utf-8 -*-
"""Unit tests for coverage palette and legend entries."""

from coverage_palette import SIGNAL_LEVELS, build_heatmap_stops, build_legend_entries


EXPECTED_SIGNAL_LEVELS = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    (-120.0, (200, 40, 40, 0), "No service"),
]


def test_signal_levels_match_upstream_nowires_palette():
    assert SIGNAL_LEVELS == EXPECTED_SIGNAL_LEVELS


def test_build_heatmap_stops_sorts_upstream_palette_for_qgis_shader():
    assert build_heatmap_stops() == sorted(EXPECTED_SIGNAL_LEVELS, key=lambda item: item[0])


def test_build_legend_entries_preserve_upstream_labels_and_order():
    assert build_legend_entries() == EXPECTED_SIGNAL_LEVELS
