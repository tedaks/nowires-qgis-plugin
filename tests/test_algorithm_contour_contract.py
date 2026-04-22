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
    assert "QgsProcessingParameterVectorDestination" in source
    assert 'self.OUTPUT = "OUTPUT"' in source or 'OUTPUT = "OUTPUT"' in source


def test_contour_algorithm_returns_output_path_to_processing():
    source = _source_text()
    assert "return {self.OUTPUT: final_output_path}" in source
