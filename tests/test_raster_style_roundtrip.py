# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify raster style functions produce correct renderers on real QGIS raster layers."""

import os
import pytest
import numpy as np

try:
    from qgis.core import (
        QgsApplication, QgsRasterLayer, QgsColorRampShader,
        QgsSingleBandPseudoColorRenderer,
    )
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(
        not _HAS_QGIS,
        reason="QGIS integration tests require QGIS_PREFIX_PATH to be set",
    ),
    pytest.mark.qgis_integration,
]


@pytest.fixture(scope="module")
def qgis_app():
    qgis = QgsApplication([], True)
    qgis.initQgis()
    yield qgis
    qgis.exitQgis()


def _make_geotiff(path, grid, min_lat, max_lat, min_lon, max_lon):
    from NoWires.raster_io import write_geotiff
    write_geotiff(path, grid, min_lat, max_lat, min_lon, max_lon)


class TestCoverageStyleRoundtrip:
    def test_apply_coverage_style_sets_renderer(self, qgis_app, tmp_path):
        from NoWires.coverage_palette import apply_coverage_style
        tif = str(tmp_path / "coverage.tif")
        grid = np.full((20, 20), -70.0, dtype=np.float32)
        _make_geotiff(tif, grid, 47.0, 47.1, 8.0, 8.1)
        layer = QgsRasterLayer(tif, "Coverage Test")
        assert layer.isValid(), "Layer not valid: {}".format("layer load failed")
        apply_coverage_style(layer)
        renderer = layer.renderer()
        assert renderer is not None
        assert isinstance(renderer, QgsSingleBandPseudoColorRenderer)

    def test_coverage_style_has_discrete_ramp(self, qgis_app, tmp_path):
        from NoWires.coverage_palette import apply_coverage_style
        tif = str(tmp_path / "coverage_discrete.tif")
        grid = np.full((20, 20), -70.0, dtype=np.float32)
        _make_geotiff(tif, grid, 47.0, 47.1, 8.0, 8.1)
        layer = QgsRasterLayer(tif, "Coverage Discrete")
        assert layer.isValid()
        apply_coverage_style(layer)
        renderer = layer.renderer()
        shader = renderer.shader()
        func = shader.rasterShaderFunction()
        assert isinstance(func, QgsColorRampShader)
        assert func.colorRampType() == QgsColorRampShader.Discrete

    def test_coverage_style_ramp_items_match_signal_levels(self, qgis_app, tmp_path):
        from NoWires.coverage_palette import apply_coverage_style, SIGNAL_LEVELS
        tif = str(tmp_path / "coverage_ramp.tif")
        grid = np.full((20, 20), -70.0, dtype=np.float32)
        _make_geotiff(tif, grid, 47.0, 47.1, 8.0, 8.1)
        layer = QgsRasterLayer(tif, "Coverage Ramp")
        assert layer.isValid()
        apply_coverage_style(layer)
        renderer = layer.renderer()
        shader = renderer.shader()
        func = shader.rasterShaderFunction()
        items = func.colorRampItemList()
        assert len(items) >= len(SIGNAL_LEVELS), \
            "Expected >= {} ramp items, got {}".format(len(SIGNAL_LEVELS), len(items))


class TestDeltaStyleRoundtrip:
    def test_apply_delta_style_diverging(self, qgis_app, tmp_path):
        from NoWires.comparison_outputs import apply_delta_style
        tif = str(tmp_path / "delta_diverging.tif")
        grid = np.full((20, 20), 3.0, dtype=np.float32)
        _make_geotiff(tif, grid, 47.0, 47.1, 8.0, 8.1)
        layer = QgsRasterLayer(tif, "Delta Diverging")
        assert layer.isValid()
        apply_delta_style(layer, threshold_db=5.0, style="diverging")
        renderer = layer.renderer()
        assert renderer is not None
        assert isinstance(renderer, QgsSingleBandPseudoColorRenderer)
        shader = renderer.shader()
        func = shader.rasterShaderFunction()
        assert isinstance(func, QgsColorRampShader)
        items = func.colorRampItemList()
        assert len(items) >= 5

    def test_apply_delta_style_threshold(self, qgis_app, tmp_path):
        from NoWires.comparison_outputs import apply_delta_style
        tif = str(tmp_path / "delta_threshold.tif")
        grid = np.full((20, 20), 2.0, dtype=np.float32)
        _make_geotiff(tif, grid, 47.0, 47.1, 8.0, 8.1)
        layer = QgsRasterLayer(tif, "Delta Threshold")
        assert layer.isValid()
        apply_delta_style(layer, threshold_db=5.0, style="threshold")
        renderer = layer.renderer()
        assert renderer is not None
        assert isinstance(renderer, QgsSingleBandPseudoColorRenderer)