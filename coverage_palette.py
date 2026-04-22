# -*- coding: utf-8 -*-
"""Exact signal palette definitions from tedaks/nowires."""

SIGNAL_LEVELS = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    (-120.0, (200, 40, 40, 0), "No service"),
]


def build_heatmap_stops():
    """Return the exact nowires palette sorted for the QGIS shader."""
    return sorted(SIGNAL_LEVELS, key=lambda item: item[0])


def build_legend_entries():
    """Return legend entries in the original nowires top-down order."""
    return list(SIGNAL_LEVELS)
