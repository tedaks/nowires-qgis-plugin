# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for coverage comparison algorithm parameter wiring."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
COMP_SOURCES = [
    os.path.join(PLUGIN_DIR, f)
    for f in (
        "base_algorithm.py",
        "raster_io.py",
        "algorithm_coverage_comparison.py",
        "comparison_params.py",
        "comparison_add_params.py",
        "comparison_outputs.py",
        "comparison_panel.py",
        "comparison_reporting.py",
    )
]


def _comp_source():
    parts = []
    for path in COMP_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            parts.append(handle.read())
    return "\n".join(parts)


def test_comparison_algorithm_name():
    source = _comp_source()
    assert 'return "coverage_comparison"' in source


def test_comparison_algorithm_has_nothreading_flag():
    source = _comp_source()
    assert "NoThreading" in source


def test_comparison_algorithm_exposes_panel_parameters():
    source = _comp_source()
    assert "PANEL_A" in source
    assert "PANEL_B" in source


def test_comparison_algorithm_exposes_delta_style():
    source = _comp_source()
    assert "DELTA_STYLE" in source
    assert "diverging" in source


def test_comparison_algorithm_exposes_output_dir():
    source = _comp_source()
    assert "OUTPUT_DIR" in source
    assert "QgsProcessingParameterFolderDestination" in source


def test_comparison_algorithm_checks_cancellation():
    source = _comp_source()
    assert "feedback.isCanceled()" in source


def test_comparison_algorithm_uses_queue_layer_for_loading():
    source = _comp_source()
    assert "queue_layer_for_loading" in source
    assert "processing_utils" in source


def test_comparison_algorithm_rx_override_is_correct():
    source = _comp_source()
    assert "rx_override=rx_clutter_override" in source
    assert "rx_override=tx_clutter_override" not in source


def test_comparison_algorithm_escapes_html():
    source = _comp_source()
    assert "html.escape" in source


def test_comparison_algorithm_gdal_null_check():
    source = _comp_source()
    assert "if ds is None" in source or "if ds_delta is None" in source


def test_comparison_algorithm_report_error_handling():
    source = _comp_source()
    assert "except OSError" in source
    assert "pushWarning" in source


def test_comparison_algorithm_uses_shared_tempdir():
    source = _comp_source()
    assert "_comp_tmp" in source
    assert "TempDirManager" in source
    assert "shutil.rmtree(_comp_tmpdir" not in source


def test_comparison_algorithm_uses_output_dir_for_each_missing_output():
    source = _comp_source()
    assert "if output_dir:" in source
    assert '"coverage_a.tif"' in source
    assert '"coverage_b.tif"' in source
    assert '"coverage_delta.tif"' in source


def test_comparison_algorithm_gdal_try_finally():
    source = _comp_source()
    assert "finally:" in source
    assert "ds_delta = None" in source or "ds = None" in source


def test_comparison_algorithm_tx_position_warning():
    source = _comp_source()
    assert "QgsProcessingException" in source
    assert "TX positions differ" in source


def test_comparison_algorithm_allows_negative_antenna_gains():
    source = _comp_source()
    assert '"gain_param"' in source
    assert 'f"{prefix}_TX_GAIN",' in source
    assert 'f"{prefix}_RX_GAIN",' in source
    assert 'config["gain_param"]' in source
