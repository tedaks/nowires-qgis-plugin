# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Extended regression tests for coverage opacity covering missed lines.

The find_latest_coverage_layer tests cover lines 50-60 (layer lookup by
project settings and by layer name fallback).  CoverageOpacityDialog
tests are not included here because instantiating QDialog in a headless
QGIS Docker container causes a Qt segfault (line 67 → QDialog.__init__).
Those covered lines (72, 115-118, 122-127) remain exercised by the
existing manual opacity-dialog workflow in the QGIS GUI.
"""

from unittest import mock

import pytest


@pytest.mark.qgis_integration
def test_find_latest_coverage_layer_by_settings():
    from NoWires.radio_coverage.opacity import find_latest_coverage_layer

    layer_stub = mock.MagicMock()
    project = mock.MagicMock()
    project.readEntry.return_value = ("layer_abc", True)
    project.mapLayer.return_value = layer_stub
    with mock.patch("NoWires.radio_coverage.opacity.QgsProject") as mock_qgs:
        mock_qgs.instance.return_value = project
        result = find_latest_coverage_layer()
    assert result is layer_stub


@pytest.mark.qgis_integration
def test_find_latest_coverage_layer_by_name_fallback():
    from NoWires.radio_coverage.opacity import find_latest_coverage_layer

    layer_a = mock.MagicMock()
    layer_a.name.return_value = "Coverage (900 MHz, 5 km, 128x128)"
    layer_b = mock.MagicMock()
    layer_b.name.return_value = "Some Other Layer"

    project = mock.MagicMock()
    project.readEntry.return_value = ("", False)
    project.mapLayers.return_value = {"a": layer_a, "b": layer_b}
    with mock.patch("NoWires.radio_coverage.opacity.QgsProject") as mock_qgs:
        mock_qgs.instance.return_value = project
        result = find_latest_coverage_layer()
    assert result is layer_a


@pytest.mark.qgis_integration
def test_find_latest_coverage_layer_none():
    from NoWires.radio_coverage.opacity import find_latest_coverage_layer

    project = mock.MagicMock()
    project.readEntry.return_value = ("", False)
    project.mapLayers.return_value = {}
    with mock.patch("NoWires.radio_coverage.opacity.QgsProject") as mock_qgs:
        mock_qgs.instance.return_value = project
        result = find_latest_coverage_layer()
    assert result is None
