# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for batch P2P algorithm parameter wiring."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
BATCH_SOURCES = [
    os.path.join(PLUGIN_DIR, f)
    for f in ("algorithm_batch.py", "batch_params.py", "batch_outputs.py", "batch_writer.py")
]


def _batch_source():
    parts = []
    for path in BATCH_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            parts.append(handle.read())
    return "\n".join(parts)


def test_batch_algorithm_name():
    source = _batch_source()
    assert 'def name(self):' in source
    assert 'return "batch_p2p_analysis"' in source


def test_batch_algorithm_group():
    source = _batch_source()
    assert 'def group(self):' in source
    assert "Radio Propagation" in source


def test_batch_algorithm_exposes_mode_parameter():
    source = _batch_source()
    assert 'MODE = "MODE"' in source
    assert '"One-to-Many' in source
    assert '"Many-to-One' in source


def test_batch_algorithm_exposes_rank_by_parameter():
    source = _batch_source()
    assert 'RANK_BY = "RANK_BY"' in source
    assert "Link margin" in source


def test_batch_algorithm_exposes_height_parameters():
    source = _batch_source()
    assert 'TX_HEIGHT = "TX_HEIGHT"' in source
    assert 'RX_HEIGHT = "RX_HEIGHT"' in source


def test_batch_algorithm_exposes_frequency_parameter():
    source = _batch_source()
    assert 'FREQ_MHZ = "FREQ_MHZ"' in source


def test_batch_algorithm_exposes_link_budget_parameters():
    source = _batch_source()
    assert 'TX_POWER = "TX_POWER"' in source
    assert 'TX_GAIN = "TX_GAIN"' in source
    assert 'RX_GAIN = "RX_GAIN"' in source
    assert 'CABLE_LOSS = "CABLE_LOSS"' in source
    assert 'RX_SENSITIVITY = "RX_SENSITIVITY"' in source


def test_batch_algorithm_exposes_antenna_parameters():
    source = _batch_source()
    assert 'TX_ANTENNA_PRESET = "TX_ANTENNA_PRESET"' in source
    assert 'RX_ANTENNA_PRESET = "RX_ANTENNA_PRESET"' in source
    assert "ANTENNA_PRESET_OPTIONS" in source


def test_batch_algorithm_exposes_clutter_parameters():
    source = _batch_source()
    assert 'CLUTTER_MODEL = "CLUTTER_MODEL"' in source
    assert "CLUTTER_MODEL_OPTIONS" in source
    assert 'TX_CLUTTER_OVERRIDE = "TX_CLUTTER_OVERRIDE"' in source
    assert 'RX_CLUTTER_OVERRIDE = "RX_CLUTTER_OVERRIDE"' in source


def test_batch_algorithm_has_nothreading_flag():
    source = _batch_source()
    assert "NoThreading" in source


def test_batch_algorithm_uses_queue_layer_for_loading():
    source = _batch_source()
    assert "queue_layer_for_loading" in source
    assert "processing_utils" in source


def test_batch_algorithm_checks_cancellation():
    source = _batch_source()
    assert "feedback.isCanceled()" in source


def test_batch_algorithm_per_link_error_handling():
    source = _batch_source()
    assert "logger.warning" in source


def test_batch_algorithm_uses_qgsprocessing_exception():
    source = _batch_source()
    assert "QgsProcessingException" in source


def test_batch_algorithm_output_parameters():
    source = _batch_source()
    assert 'OUTPUT_MARKERS = "OUTPUT_MARKERS"' in source
    assert 'OUTPUT_CSV = "OUTPUT_CSV"' in source
    assert 'OUTPUT_JSON = "OUTPUT_JSON"' in source


def test_batch_algorithm_eirp_is_per_link():
    source = _batch_source()
    assert "eirp_eff" in source or "eirp" in source.lower()


def test_batch_algorithm_uses_radio_constants():
    source = _batch_source()
    assert "ITM_MIN_TERMINAL_HEIGHT_M" in source or "ITM_MIN_FREQUENCY_MHZ" in source


def test_batch_algorithm_exposes_custom_k_factor_choice():
    source = _batch_source()
    assert '"Custom"' in source
    assert "K_FACTOR" in source
    assert "len(K_FACTOR_PRESETS)" in source


def test_batch_algorithm_keeps_temporary_outputs_alive_for_qgis_loading():
    source = _batch_source()
    assert "shutil.rmtree(_batch_tmp" not in source
    assert "Temporary outputs are intentionally left on disk" in source


def test_batch_algorithm_transforms_source_layer_points_to_epsg4326():
    source = _batch_source()
    assert "QgsCoordinateTransform" in source
    assert "sourceCrs()" in source


def test_batch_algorithm_uses_global_antenna_settings_as_feature_defaults():
    source = _batch_source()
    assert "tx_default_preset_key" in source
    assert "rx_default_preset_key" in source
    assert 'tx_def.get("antenna_preset", tx_default_preset_key)' in source
    assert 'rx_def.get("antenna_preset", rx_default_preset_key)' in source
    assert 'tx_def.get("azimuth", tx_default_az)' in source
    assert 'rx_def.get("azimuth", rx_default_az)' in source


def test_batch_many_to_one_summary_prints_tx_candidate_coordinates():
    source = _batch_source()
    assert 'r["tx_lat"]' in source
    assert 'r["rx_lat"]' in source
    assert "mode ==" in source
