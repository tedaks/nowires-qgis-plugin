# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test: P2P chart failure must push a warning to feedback.

Before v1.6.1, when show_profile_chart raised an exception, only the logger
was informed — the user saw no feedback. The fix calls feedback.pushWarning().
"""

import os
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "p2p/compute.py"))

_MINIMAL_KWARGS = {
    "f_mhz": 900, "dist_m": 5000, "tx_h": 10, "rx_h": 10,
    "tx_power": 20, "tx_gain": 6, "rx_gain": 2, "cable_loss": 1,
    "rx_sens": -100, "prx_dbm": -60, "margin_db": 12,
    "itm_loss_db": 120, "result": MagicMock(), "k_factor": 1.33,
    "distances": [], "elevations": [], "terrain_bulge": [],
    "los_h": [], "fresnel_r": [],
}


def _call_load_layers(mock_feedback=None, show_chart=True):
    """Call _load_p2p_qgis_layers with all internal dependencies mocked."""
    import NoWires.p2p.compute as compute_mod
    mock_context = MagicMock()
    mock_layer = MagicMock()
    mock_layer.isValid.return_value = True
    mock_renderer = MagicMock()
    mock_renderer.rootRule.return_value = MagicMock()
    with patch.object(compute_mod, "show_profile_chart", side_effect=RuntimeError("chart crash")), \
         patch("qgis.core.QgsVectorLayer", return_value=mock_layer), \
         patch("qgis.core.QgsRuleBasedRenderer", return_value=mock_renderer, create=True), \
         patch("NoWires.p2p.symbology.QgsRuleBasedRenderer", return_value=mock_renderer, create=True), \
         patch("NoWires.p2p.symbology.QgsSymbol.defaultSymbol", return_value=MagicMock()), \
         patch.object(compute_mod, "register_destination_layer", return_value=None), \
         patch.object(compute_mod, "queue_layer_for_loading"):
        compute_mod._load_p2p_qgis_layers(
            context=mock_context,
            profile_path="/tmp/profile.shp",
            fresnel_poly_path="/tmp/fresnel.shp",
            fresnel_lines_path="/tmp/flines.shp",
            markers_path="/tmp/markers.shp",
            show_chart=show_chart,
            chart_kwargs=_MINIMAL_KWARGS,
            sink=[],
            feedback=mock_feedback,
        )


def test_chart_failure_pushes_warning_to_feedback():
    """When show_profile_chart raises, feedback.pushWarning must be called."""
    mock_feedback = MagicMock()
    _call_load_layers(mock_feedback=mock_feedback, show_chart=True)
    mock_feedback.pushWarning.assert_called_once_with("P2P profile chart creation failed")


def test_chart_failure_no_feedback_does_not_crash():
    """When feedback is None, chart failure must not crash."""
    _call_load_layers(mock_feedback=None, show_chart=True)


def test_source_contains_push_warning():
    """Source-level contract: _load_p2p_qgis_layers must call feedback.pushWarning."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert 'pushWarning("P2P profile chart creation failed")' in source, (
        "p2p/compute.py must call feedback.pushWarning when chart creation fails"
    )