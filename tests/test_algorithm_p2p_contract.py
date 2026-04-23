# -*- coding: utf-8 -*-
"""Regression tests for point-to-point algorithm parameter wiring."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
P2P_SOURCE = os.path.join(PLUGIN_DIR, "algorithm_p2p.py")


def _p2p_source():
    with open(P2P_SOURCE, "r", encoding="utf-8") as handle:
        return handle.read()


def test_p2p_algorithm_exposes_itm_variability_parameters():
    source = _p2p_source()
    assert 'TIME_PCT = "TIME_PCT"' in source
    assert 'LOCATION_PCT = "LOCATION_PCT"' in source
    assert 'SITUATION_PCT = "SITUATION_PCT"' in source
    assert '"Time percentage"' in source
    assert '"Location percentage"' in source
    assert '"Situation percentage"' in source
    assert "defaultValue=50.0" in source
    assert "minValue=0.01" in source
    assert "maxValue=99.99" in source


def test_p2p_algorithm_forwards_itm_variability_parameters():
    source = _p2p_source()
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


def test_p2p_algorithm_defaults_polarization_to_vertical():
    source = _p2p_source()
    expected_block = """QgsProcessingParameterEnum(
                self.POLARIZATION,
                "Polarization",
                options=["Horizontal", "Vertical"],
                defaultValue=1,"""
    assert expected_block in source


def test_p2p_algorithm_exposes_k_factor_preset_and_legacy_numeric_parameter():
    source = _p2p_source()
    expected_block = """QgsProcessingParameterEnum(
                self.K_FACTOR_PRESET,
                "Earth radius factor preset (k)",
                options=[
                    "0.67 - Sub-refractive",
                    "1.00 - Geometric",
                    "1.33 - Standard atmosphere",
                    "2.00 - Super-refractive",
                    "4.00 - Strong super-refractive",
                ],
                defaultValue=2,"""
    assert expected_block in source
    assert 'K_FACTOR_PRESET = "K_FACTOR_PRESET"' in source
    assert 'K_FACTOR = "K_FACTOR"' in source
    assert '"Custom Earth radius factor (k)"' in source
    assert "QgsProcessingParameterNumber(" in source


def test_p2p_algorithm_keeps_legacy_k_factor_as_compatibility_fallback():
    source = _p2p_source()
    assert "if self.K_FACTOR_PRESET not in parameters and self.K_FACTOR in parameters:" in source
    assert "k_factor = self.parameterAsDouble(parameters, self.K_FACTOR, context)" in source
    assert "k_factor = K_FACTOR_PRESETS[" in source


def test_p2p_algorithm_exposes_marker_output():
    source = _p2p_source()
    assert 'OUTPUT_MARKERS = "OUTPUT_MARKERS"' in source
    assert '"TX/RX marker output"' in source


def test_p2p_algorithm_exposes_report_outputs():
    source = _p2p_source()
    assert 'OUTPUT_REPORT_CSV = "OUTPUT_REPORT_CSV"' in source
    assert 'OUTPUT_REPORT_JSON = "OUTPUT_REPORT_JSON"' in source
    assert 'OUTPUT_REPORT_HTML = "OUTPUT_REPORT_HTML"' in source
    assert "QgsProcessingParameterFileDestination(" in source
    assert '"P2P report CSV"' in source
    assert '"P2P report JSON"' in source
    assert '"P2P report HTML"' in source


def test_p2p_algorithm_returns_marker_and_report_outputs():
    source = _p2p_source()
    assert "self.OUTPUT_MARKERS: markers_path" in source
    assert "self.OUTPUT_REPORT_CSV: report_csv_path" in source
    assert "self.OUTPUT_REPORT_JSON: report_json_path" in source
    assert "self.OUTPUT_REPORT_HTML: report_html_path" in source


def test_p2p_algorithm_reports_reliability_fields():
    source = _p2p_source()
    assert "availability_method" in source
    assert "availability_estimate_pct" in source
    assert "fade_margin_class" in source
    assert "reliability_summary" in source
