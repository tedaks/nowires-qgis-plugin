# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for the contour Processing output contract."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
CONTOUR_SOURCES = [
    os.path.join(PLUGIN_DIR, f)
    for f in (
        "algorithm_contour.py",
        "contour_smoothing.py",
        "contour_overlay.py",
        "contour_symbology.py",
        "contour_generation.py",
        "contour_pipeline.py",
    )
]


def _source_text():
    parts = []
    for path in CONTOUR_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            parts.append(handle.read())
    return "\n".join(parts)


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
    assert "ENTRY_KEY_LAST_DEM" in source
    assert "layer.id()" in source


def test_contour_algorithm_uses_processing_context_for_layer_loading():
    source = _source_text()
    assert "queue_layer_for_loading(" in source
    assert "processing_utils" in source


def test_contour_algorithm_uses_direct_qt6_painter_blend_enum():
    source = _source_text()
    assert "QPainter.CompositionMode.CompositionMode_ColorDodge" in source
    assert "painter_blend_mode_color_dodge" not in source


def test_raster_calc_explicitly_closes_gdal_datasets():
    source = _source_text()
    assert "out_ds = None" in source
    assert "while datasets:" in source
    assert "datasets.pop()" in source


def test_blur_vrt_buildvrt_releases_before_xml_parse():
    source = _source_text()
    assert "gdal.BuildVRT(vrt_path, src_path)" in source
    assert "ET.parse(vrt_path)" in source
    assert source.index("gdal.BuildVRT(vrt_path, src_path)") < source.index("ET.parse(vrt_path)")
