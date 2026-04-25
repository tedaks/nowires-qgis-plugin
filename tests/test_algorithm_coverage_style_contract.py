# -*- coding: utf-8 -*-
"""Regression tests for coverage raster styling compatibility."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
SOURCE_PATH = os.path.join(PLUGIN_DIR, "algorithm_coverage.py")


def _source_text():
    with open(SOURCE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_coverage_algorithm_imports_qgsrastershader():
    source = _source_text()
    assert "QgsRasterShader" in source


def test_coverage_algorithm_wraps_color_ramp_shader():
    source = _source_text()
    assert "shader = QgsRasterShader()" in source
    assert "shader.setRasterShaderFunction(color_ramp_shader)" in source


def test_coverage_algorithm_passes_raster_shader_to_renderer():
    source = _source_text()
    assert "renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)" in source


def test_coverage_algorithm_uses_heatmap_stop_builder():
    source = _source_text()
    assert "from .coverage_palette import build_heatmap_stops" in source
    assert "for value, rgba, label in build_heatmap_stops()" in source


def test_coverage_algorithm_uses_interpolated_palette():
    source = _source_text()
    assert (
        "color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)" in source
    )


def test_coverage_algorithm_sets_full_opacity_on_layer():
    source = _source_text()
    assert "raster_layer.setOpacity(1.0)" in source


def test_coverage_algorithm_has_no_transparency_slider():
    source = _source_text()
    assert "TransparencySliderWidget" not in source
    assert "WidgetWrapper" not in source
    assert "slider_orientation_horizontal" not in source
