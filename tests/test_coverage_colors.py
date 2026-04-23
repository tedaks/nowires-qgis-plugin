# -*- coding: utf-8 -*-
"""Regression tests for coverage color mapping helpers."""

import importlib

import numpy as np


def test_color_module_exists():
    module = importlib.import_module("NoWires.coverage_colors")
    assert hasattr(module, "apply_coverage_colors")


def test_apply_coverage_colors_maps_thresholds_and_nan():
    module = importlib.import_module("NoWires.coverage_colors")

    prx_grid = np.array([[-50.0, -90.0], [np.nan, -130.0]], dtype=np.float64)
    thresholds = np.array([-60.0, -100.0], dtype=np.float64)
    colors = np.array(
        [
            [10, 20, 30, 255],
            [40, 50, 60, 200],
            [70, 80, 90, 150],
        ],
        dtype=np.uint8,
    )
    rgba_out = np.zeros((2, 2, 4), dtype=np.uint8)

    module.apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    assert rgba_out.tolist() == [
        [[0, 0, 0, 0], [70, 80, 90, 150]],
        [[10, 20, 30, 255], [40, 50, 60, 200]],
    ]
