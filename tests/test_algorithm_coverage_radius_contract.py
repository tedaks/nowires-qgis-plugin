# -*- coding: utf-8 -*-
"""Regression tests for the coverage radius Processing output contract."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
SOURCE_PATH = os.path.join(PLUGIN_DIR, "algorithm_coverage_radius.py")


def _source_text():
    with open(SOURCE_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_coverage_radius_algorithm_declares_output_destination_parameter():
    source = _source_text()
    assert "QgsProcessingParameterVectorDestination" in source
    assert 'self.OUTPUT = "OUTPUT"' in source or 'OUTPUT = "OUTPUT"' in source


def test_coverage_radius_algorithm_returns_processing_output_path():
    source = _source_text()
    assert "return {self.OUTPUT: final_output_path}" in source


def test_coverage_radius_algorithm_does_not_force_shapefile_suffix():
    source = _source_text()
    assert 'output_dest.lower().endswith(".shp")' not in source
    assert 'output_dest = output_dest + ".shp"' not in source
