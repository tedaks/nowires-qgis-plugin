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
    assert (
        'feedback.pushInfo("Max usable distance:' in source
        or "Max usable distance:" in source
    )
    assert (
        'feedback.pushInfo("Average usable distance:' in source
        or "Average usable distance:" in source
    )


def test_coverage_algorithm_uses_preset_grid_sizes():
    source = _coverage_source()
    assert "QgsProcessingParameterEnum(" in source
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
    assert (
        "time_pct = self.parameterAsDouble(parameters, self.TIME_PCT, context)"
        in source
    )
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


def test_coverage_profile_step_helper_returns_finer_sampling():
    """Behavioural replacement for the literal-string check.

    The algorithm delegates the profile sampling step to a pure helper
    in ``coverage_compute``. We verify the helper's contract directly so
    the test survives source reformatting and frequency-aware tuning.
    """
    from coverage_compute import (
        DEFAULT_MAX_PROFILE_PTS,
        coverage_profile_step_m,
    )

    assert coverage_profile_step_m(300.0) == 100.0
    # Helper accepts any positive frequency without raising.
    for f_mhz in (40.0, 300.0, 5800.0):
        assert coverage_profile_step_m(f_mhz) > 0.0
    assert DEFAULT_MAX_PROFILE_PTS == 200


def test_coverage_algorithm_wires_profile_step_helper():
    """The algorithm must call the helper rather than baking in a literal."""
    source = _coverage_source()
    assert "from .coverage_compute import" in source
    assert "coverage_profile_step_m" in source
    assert "DEFAULT_MAX_PROFILE_PTS" in source
    assert "profile_step_m=coverage_profile_step_m(" in source
    assert "max_profile_pts=DEFAULT_MAX_PROFILE_PTS" in source


def test_coverage_algorithm_sets_full_opacity():
    source = _coverage_source()
    assert "raster_layer.setOpacity(1.0)" in source


def test_coverage_algorithm_has_no_transparency_parameter():
    source = _coverage_source()
    assert "OVERLAY_TRANSPARENCY" not in source
    assert "Overlay transparency" not in source
    assert "TransparencySliderWidget" not in source


def test_coverage_algorithm_disables_threading():
    source = _coverage_source()
    assert "NoThreading" in source


def test_coverage_algorithm_loads_dem_as_elevation_layer():
    source = _coverage_source()
    assert 'QgsRasterLayer(dem_path, "NoWires DEM (GLO-30)")' in source
    assert "elevationProperties()" in source
    assert "elev_props.setEnabled(True)" in source
    assert "Qgis.RasterElevationMode.RepresentsElevationSurface" in source
    assert "elev_props.setBandNumber(1)" in source
    assert '_queue_layer_for_loading(context, dem_layer, "NoWires DEM (GLO-30)")' in source


def test_coverage_algorithm_exposes_report_outputs():
    source = _coverage_source()
    assert 'OUTPUT_REPORT_CSV = "OUTPUT_REPORT_CSV"' in source
    assert 'OUTPUT_REPORT_JSON = "OUTPUT_REPORT_JSON"' in source
    assert 'OUTPUT_REPORT_HTML = "OUTPUT_REPORT_HTML"' in source
    assert "QgsProcessingParameterFileDestination(" in source
    assert '"Coverage report CSV"' in source
    assert '"Coverage report JSON"' in source
    assert '"Coverage report HTML"' in source


def test_coverage_algorithm_returns_report_outputs():
    source = _coverage_source()
    assert "self.OUTPUT_REPORT_CSV: report_csv_path" in source
    assert "self.OUTPUT_REPORT_JSON: report_json_path" in source
    assert "self.OUTPUT_REPORT_HTML: report_html_path" in source


def test_coverage_algorithm_reports_reliability_fields():
    source = _coverage_source()
    assert "availability_method" in source
    assert "availability_estimate_pct" in source
    assert "fade_margin_class" in source
    assert "reliability_summary" in source


def test_coverage_algorithm_builds_report_payload_before_logging_reliability():
    source = _coverage_source()
    build_idx = source.index("report_payload = build_coverage_report_payload(")
    log_idx = source.index(
        'feedback.pushInfo(\n                    "Availability method: {}'.replace("\\n", "\n"),
        build_idx,
    )
    assert build_idx < log_idx


def test_coverage_algorithm_constrains_inputs_to_bundled_itm_limits():
    source = _coverage_source()
    assert "validate_itm_input_ranges(" in source
    assert "maxValue=ITM_MAX_TERMINAL_HEIGHT_M" in source
    assert "minValue=ITM_MIN_FREQUENCY_MHZ" in source
    assert "maxValue=ITM_MAX_FREQUENCY_MHZ" in source
    assert "minValue=ITM_MIN_N0" in source
    assert "maxValue=ITM_MAX_N0" in source
    assert "minValue=ITM_MIN_SIGMA" in source


def test_coverage_algorithm_writes_reports_even_when_no_pixels_are_valid():
    source = _coverage_source()
    assert "if not valid.any():" in source
    assert "build_empty_coverage_report_payload(" in source
    empty_idx = source.index("build_empty_coverage_report_payload(")
    write_idx = source.index("write_report_csv(report_csv_path, report_payload)")
    assert empty_idx < write_idx


def test_coverage_algorithm_uses_processing_context_for_layer_loading():
    source = _coverage_source()
    assert "_queue_layer_for_loading(" in source
    assert "context.temporaryLayerStore().addMapLayer(layer)" in source
    assert "addLayerToLoadOnCompletion" in source
    assert "QgsProject.instance().addMapLayer(" not in source
