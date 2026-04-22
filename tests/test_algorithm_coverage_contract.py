# -*- coding: utf-8 -*-
"""Regression tests for coverage algorithm naming and wiring."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
COVERAGE_SOURCE = os.path.join(PLUGIN_DIR, "algorithm_coverage.py")


def _coverage_source():
    with open(COVERAGE_SOURCE, "r", encoding="utf-8") as handle:
        return handle.read()


def test_coverage_algorithm_uses_new_processing_id_and_label():
    source = _coverage_source()
    assert 'return "coverage_analysis"' in source
    assert 'return self.tr("Coverage Analysis")' in source


def test_coverage_algorithm_uses_raster_summary_helper_for_range_metrics():
    source = _coverage_source()
    assert "from .coverage_summary import summarize_coverage_grid" in source
    assert "summary = summarize_coverage_grid(" in source
    assert 'feedback.pushInfo("Max usable distance:' in source
    assert 'feedback.pushInfo("Average usable distance:' in source


def test_coverage_algorithm_uses_preset_grid_sizes():
    source = _coverage_source()
    assert 'QgsProcessingParameterEnum(' in source
    assert '"Grid size resolution"' in source
    assert '"64 x 64"' in source
    assert '"128 x 128"' in source
    assert '"192 x 192"' in source
    assert '"256 x 256"' in source
    assert '"384 x 384"' in source
    assert '"512 x 512"' in source
    assert '"768 x 768"' in source
    assert '"1024 x 1024"' in source


def test_coverage_algorithm_labels_radius_as_max_analysis_distance():
    source = _coverage_source()
    expected_block = """QgsProcessingParameterNumber(
                self.RADIUS_KM,
                "Max analysis distance (km)","""
    assert expected_block in source


def test_coverage_algorithm_defaults_polarization_to_vertical():
    source = _coverage_source()
    assert 'options=["Horizontal", "Vertical"]' in source
    assert "defaultValue=1" in source


def test_coverage_algorithm_shows_map_legend():
    source = _coverage_source()
    assert "from .coverage_legend import show_coverage_legend" in source
    assert "show_coverage_legend(rx_sensitivity_dbm=rx_sens)" in source


def test_coverage_algorithm_exposes_itm_variability_parameters():
    source = _coverage_source()
    assert 'TIME_PCT = "TIME_PCT"' in source
    assert 'LOCATION_PCT = "LOCATION_PCT"' in source
    assert 'SITUATION_PCT = "SITUATION_PCT"' in source
    assert '"Time percentage"' in source
    assert '"Location percentage"' in source
    assert '"Situation percentage"' in source
    assert "defaultValue=50.0" in source
    assert "minValue=0.01" in source
    assert "maxValue=99.99" in source


def test_coverage_algorithm_forwards_itm_variability_parameters():
    source = _coverage_source()
    assert "time_pct = self.parameterAsDouble(parameters, self.TIME_PCT, context)" in source
    assert (
        "location_pct = self.parameterAsDouble(parameters, self.LOCATION_PCT, context)"
        in source
    )
    assert (
        "situation_pct = self.parameterAsDouble(parameters, self.SITUATION_PCT, context)"
        in source
    )
    assert "time_pct=time_pct," in source
    assert "location_pct=location_pct," in source
    assert "situation_pct=situation_pct," in source


def test_coverage_algorithm_uses_finer_profile_sampling():
    source = _coverage_source()
    assert "profile_step_m=100.0," in source
    assert "max_profile_pts=200," in source


def test_coverage_algorithm_exposes_overlay_transparency_parameter():
    source = _coverage_source()
    assert 'OVERLAY_TRANSPARENCY = "OVERLAY_TRANSPARENCY"' in source
    assert '"Overlay transparency (%)"' in source
    assert "type=QgsProcessingParameterNumber.Integer" in source
    assert "defaultValue=35" in source
    assert "minValue=0" in source
    assert "maxValue=100" in source
