# -*- coding: utf-8 -*-
"""Regression tests for the contour Processing output contract."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
SOURCE_PATH = os.path.join(PLUGIN_DIR, "algorithm_contour.py")


def _source_text():
    with open(SOURCE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_contour_algorithm_declares_output_destination_parameter():
    source = _source_text()
    assert "QgsProcessingParameterFileDestination" in source
    assert '"Contour lines output"' in source
    assert 'self.OUTPUT = "OUTPUT"' in source or 'OUTPUT = "OUTPUT"' in source


def test_contour_algorithm_returns_output_path_to_processing():
    source = _source_text()
    assert "return {self.OUTPUT: final_output_path" in source


def test_contour_algorithm_declares_optional_dem_output_for_3d():
    source = _source_text()
    assert "QgsProcessingParameterFileDestination" in source
    assert 'OUTPUT_DEM = "OUTPUT_DEM"' in source
    assert '"Raw DEM output (3D terrain)"' in source


def test_contour_algorithm_stores_latest_3d_layer_ids():
    source = _source_text()
    assert '"last_contour_layer_id"' in source
    assert '"last_dem_layer_id"' in source
    assert "layer.id()" in source


def test_contour_algorithm_uses_processing_context_for_layer_loading():
    source = _source_text()
    assert "_queue_layer_for_loading(" in source
    assert "context.temporaryLayerStore().addMapLayer(layer)" in source
    assert "addLayerToLoadOnCompletion" in source
    assert "QgsProject.instance().addMapLayer(" not in source
