# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for coverage raster styling compatibility."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
PALETTE_SOURCE_PATH = os.path.join(PLUGIN_DIR, "coverage_palette.py")
ALGORITHM_SOURCES = [
    os.path.join(PLUGIN_DIR, f)
    for f in (
        "algorithm_coverage.py",
        "coverage_params.py",
        "coverage_reporting.py",
        "coverage_pool.py",
        "coverage_tasks.py",
    )
]


def _palette_source():
    with open(PALETTE_SOURCE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def _algorithm_source():
    parts = []
    for path in ALGORITHM_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            parts.append(handle.read())
    return "\n".join(parts)


def test_coverage_algorithm_delegates_to_palette():
    source = _algorithm_source()
    assert "from .coverage_palette import apply_coverage_style" in source
    assert "apply_coverage_style(layer)" in source


def test_palette_function_imports_qgsrastershader():
    source = _palette_source()
    assert "QgsRasterShader" in source


def test_palette_function_wraps_color_ramp_shader():
    source = _palette_source()
    assert "shader = QgsRasterShader()" in source
    assert "shader.setRasterShaderFunction(color_ramp_shader)" in source


def test_palette_function_passes_raster_shader_to_renderer():
    source = _palette_source()
    assert "renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)" in source


def test_palette_function_uses_heatmap_stop_builder():
    source = _palette_source()
    assert "for value, rgba, label in build_heatmap_stops()" in source


def test_palette_function_uses_interpolated_palette():
    source = _palette_source()
    assert (
        "color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)" in source
    )


def test_coverage_algorithm_sets_full_opacity_on_layer():
    source = _algorithm_source()
    assert "raster_layer.setOpacity(1.0)" in source


def test_coverage_algorithm_has_no_transparency_slider():
    source = _algorithm_source()
    assert "TransparencySliderWidget" not in source
    assert "WidgetWrapper" not in source
    assert "slider_orientation_horizontal" not in source