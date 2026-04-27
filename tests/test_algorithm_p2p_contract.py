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


def test_resolve_k_factor_prefers_preset_when_available():
    """Behavioural replacement for the literal-string check on parameter wiring.

    The algorithm delegates k-factor selection to a pure helper. Asserting
    on the helper's behaviour is robust to source reformatting and to the
    exact shape of the preset-vs-custom branch in ``processAlgorithm``.
    """
    from radio import K_FACTOR_PRESETS, resolve_k_factor

    # Preset present -> use the preset, ignore the custom value.
    assert (
        resolve_k_factor(
            has_preset=True,
            has_custom=True,
            custom_value=99.0,
            preset_index=2,
        )
        == K_FACTOR_PRESETS[2]
    )

    # Only the legacy custom field present -> fall back to the custom value.
    assert (
        resolve_k_factor(
            has_preset=False,
            has_custom=True,
            custom_value=2.5,
            preset_index=0,
        )
        == 2.5
    )

    # Neither flagged as present -> still resolve via the preset index
    # (matches the algorithm's else-branch when both flags are False).
    assert (
        resolve_k_factor(
            has_preset=False,
            has_custom=False,
            custom_value=0.0,
            preset_index=1,
        )
        == K_FACTOR_PRESETS[1]
    )


def test_p2p_algorithm_wires_resolve_k_factor_helper():
    """The algorithm must delegate to the helper, not inline the branch."""
    source = _p2p_source()
    assert "resolve_k_factor" in source
    assert "K_FACTOR_PRESETS[" not in source, (
        "Algorithm should call resolve_k_factor instead of indexing presets directly"
    )


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


def test_p2p_algorithm_constrains_inputs_to_bundled_itm_limits():
    source = _p2p_source()
    assert "validate_itm_input_ranges(" in source
    assert "maxValue=ITM_MAX_TERMINAL_HEIGHT_M" in source
    assert "minValue=ITM_MIN_FREQUENCY_MHZ" in source
    assert "maxValue=ITM_MAX_FREQUENCY_MHZ" in source
    assert "minValue=ITM_MIN_N0" in source
    assert "maxValue=ITM_MAX_N0" in source
    assert "minValue=ITM_MIN_SIGMA" in source


def test_p2p_algorithm_uses_processing_context_for_layer_loading():
    source = _p2p_source()
    assert "_queue_layer_for_loading(" in source
    assert "context.temporaryLayerStore().addMapLayer(layer)" in source
    assert "addLayerToLoadOnCompletion" in source
    assert "QgsProject.instance().addMapLayer(" not in source


def test_p2p_algorithm_removes_existing_profile_and_fresnel_outputs():
    source = _p2p_source()
    assert "_remove_existing_ogr_dataset(driver, path)" in source
    assert "_remove_existing_ogr_dataset(poly_driver, poly_path)" in source
    assert "_remove_existing_ogr_dataset(lines_driver, lines_path)" in source


def test_p2p_profile_chart_uses_direct_qt6_enums():
    source = _p2p_source()
    assert "Qt.WidgetAttribute.WA_DeleteOnClose" in source
    assert "Qt.DockWidgetArea.RightDockWidgetArea" in source
    assert "widget_attribute_delete_on_close" not in source
    assert "dock_widget_area_right" not in source


def test_p2p_algorithm_exposes_antenna_and_clutter_parameters():
    source = _p2p_source()
    assert 'TX_ANTENNA_PRESET = "TX_ANTENNA_PRESET"' in source
    assert 'RX_ANTENNA_PRESET = "RX_ANTENNA_PRESET"' in source
    assert 'TX_FRONT_BACK_DB = "TX_FRONT_BACK_DB"' in source
    assert 'TX_DOWNTILT_DEG = "TX_DOWNTILT_DEG"' in source
    assert 'CLUTTER_MODEL = "CLUTTER_MODEL"' in source
    assert 'CLUTTER_RASTER = "CLUTTER_RASTER"' in source
    assert 'TX_CLUTTER_OVERRIDE = "TX_CLUTTER_OVERRIDE"' in source
    assert 'RX_CLUTTER_OVERRIDE = "RX_CLUTTER_OVERRIDE"' in source


def test_p2p_algorithm_reports_total_path_loss_components():
    source = _p2p_source()
    assert "total_path_loss_db" in source
    assert "clutter_tx_db" in source
    assert "clutter_rx_db" in source
    assert "antenna_gain_adjustment_db" in source
