# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test: comparison panel must raise QgsProcessingException, not ValueError.

Before v1.6.1, comparison/panel.py raised ValueError when the clutter grid
was unavailable, which crashes the QGIS processing framework. The fix
raises QgsProcessingException instead.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "comparison/panel.py"))


def test_panel_raises_qgsprocessingexception():
    """run_panel_coverage must raise QgsProcessingException when clutter grid unavailable."""
    from qgis.core import QgsProcessingException

    with patch("NoWires.comparison.panel.collect_panel_params") as mock_params, \
         patch("NoWires.comparison.panel.validate_itm_input_ranges"), \
         patch("NoWires.comparison.panel.ensure_clutter_grid_for_area", return_value=None):

        p = MagicMock()
        p.clutter_enabled = True
        p.clutter_raster_path = None
        p.tx_h = 10.0
        p.rx_h = 2.0
        p.f_mhz = 900.0
        p.n0 = 301.0
        p.sigma = 0.005
        p.tx_lat = 44.0
        p.tx_lon = 10.0
        p.radius_km = 5.0
        p.grid_size = 100
        mock_params.return_value = p

        from NoWires.comparison.panel import run_panel_coverage

        with pytest.raises(QgsProcessingException, match="Failed to load clutter grid"):
            run_panel_coverage(
                algorithm_instance=MagicMock(),
                prefix="A",
                parameters={},
                context=MagicMock(),
                feedback=MagicMock(),
                elev=MagicMock(),
                south=44.0,
                north=45.0,
                west=10.0,
                east=11.0,
                shared_clutter_grid=None,
            )


def test_source_uses_qgsprocessingexception():
    """Source-level check: panel.py must import and raise QgsProcessingException."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "QgsProcessingException" in source, (
        "panel.py must use QgsProcessingException, not ValueError"
    )
    assert "raise ValueError" not in source, (
        "panel.py must not raise ValueError; use QgsProcessingException"
    )