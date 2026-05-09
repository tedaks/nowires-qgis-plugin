# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Unit tests for overlay raster sizing helpers."""

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


def test_choose_overlay_dimensions_tall_narrow():
    width, height, scale = choose_overlay_dimensions(800, 4000, max_dimension=2048)
    assert width >= 1
    assert height == 2048
    assert scale < 1.0


def test_choose_overlay_dimensions_at_exact_max():
    assert choose_overlay_dimensions(2048, 1024, max_dimension=2048) == (2048, 1024, 1.0)


def test_choose_overlay_dimensions_minimum_1px():
    width, height, scale = choose_overlay_dimensions(1, 1, max_dimension=2048)
    assert width == 1
    assert height == 1
    assert scale == 1.0


def test_choose_overlay_dimensions_extreme_aspect_ratio():
    width, height, scale = choose_overlay_dimensions(10000, 10, max_dimension=2048)
    assert width == 2048
    assert height >= 1


def test_build_overview_levels_exact_boundary():
    assert build_overview_levels(512, 512, minimum_dimension=256) == [2]


def test_build_overview_levels_just_above_boundary():
    assert build_overview_levels(513, 513, minimum_dimension=256) == [2]


def test_build_overview_levels_minimum_dimension_1():
    assert build_overview_levels(16, 16, minimum_dimension=1)[0] == 2
