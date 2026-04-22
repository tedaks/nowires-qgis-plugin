# -*- coding: utf-8 -*-
"""Unit tests for overlay raster sizing helpers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from overlay_raster import build_overview_levels, choose_overlay_dimensions


def test_choose_overlay_dimensions_keeps_small_rasters_unchanged():
    assert choose_overlay_dimensions(1200, 800, max_dimension=2048) == (1200, 800, 1.0)


def test_choose_overlay_dimensions_scales_large_rasters_proportionally():
    width, height, scale = choose_overlay_dimensions(4096, 2048, max_dimension=2048)
    assert (width, height) == (2048, 1024)
    assert scale == 0.5


def test_build_overview_levels_returns_powers_of_two():
    assert build_overview_levels(2048, 1024, minimum_dimension=256) == [2, 4, 8]


def test_build_overview_levels_returns_empty_for_small_rasters():
    assert build_overview_levels(200, 150, minimum_dimension=256) == []
