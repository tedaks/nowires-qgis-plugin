# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Extended regression tests for coverage opacity covering missed lines."""

from unittest import mock

import pytest


@pytest.mark.qgis_integration
def test_find_latest_coverage_layer_by_settings():
    from qgis.core import QgsProject
    from NoWires.coverage.opacity import find_latest_coverage_layer

    mock_layer = mock.MagicMock()

    with mock.patch.object(QgsProject, "instance") as mock_instance:
        mock_project = mock.MagicMock()
        mock_instance.return_value = mock_project
        mock_project.readEntry.return_value = ("layer_123", True)
        mock_project.mapLayer.return_value = mock_layer

        result = find_latest_coverage_layer()

        assert result is mock_layer
        mock_project.readEntry.assert_called_once_with(
            "NoWires", "last_coverage_layer_id", ""
        )
        mock_project.mapLayer.assert_called_once_with("layer_123")


@pytest.mark.qgis_integration
def test_find_latest_coverage_layer_by_name_fallback():
    from qgis.core import QgsProject
    from NoWires.coverage.opacity import find_latest_coverage_layer

    mock_coverage = mock.MagicMock()
    mock_coverage.name.return_value = "Coverage (900 MHz, 5 km, 128x128)"
    mock_other = mock.MagicMock()
    mock_other.name.return_value = "Contour layer"

    with mock.patch.object(QgsProject, "instance") as mock_instance:
        mock_project = mock.MagicMock()
        mock_instance.return_value = mock_project
        mock_project.readEntry.return_value = ("", False)
        mock_project.mapLayers.return_value = {
            "id_a": mock_other,
            "id_b": mock_coverage,
        }

        result = find_latest_coverage_layer()

        assert result is mock_coverage


@pytest.mark.qgis_integration
def test_find_latest_coverage_layer_none():
    from qgis.core import QgsProject
    from NoWires.coverage.opacity import find_latest_coverage_layer

    with mock.patch.object(QgsProject, "instance") as mock_instance:
        mock_project = mock.MagicMock()
        mock_instance.return_value = mock_project
        mock_project.readEntry.return_value = ("", False)
        mock_project.mapLayers.return_value = {}

        result = find_latest_coverage_layer()

        assert result is None


@pytest.mark.qgis_integration
def test_coverage_opacity_dialog_on_slider_changed_refreshes_canvas():
    from NoWires.coverage.opacity import CoverageOpacityDialog

    mock_layer = mock.MagicMock()
    mock_layer.id.return_value = "layer_abc"
    mock_layer.name.return_value = "Coverage (1800 MHz)"
    mock_layer.opacity.return_value = 0.6

    dialog = CoverageOpacityDialog(mock_layer)

    with mock.patch.object(dialog, "_resolve_layer", return_value=mock_layer):
        with mock.patch("qgis.utils.iface") as mock_iface:
            mock_canvas = mock.MagicMock()
            mock_iface.mapCanvas.return_value = mock_canvas

            dialog._on_slider_changed(75)

            mock_layer.setOpacity.assert_called_with(0.75)
            mock_layer.triggerRepaint.assert_called_once()
            mock_canvas.refresh.assert_called_once()
            dialog._pct_label.setText.assert_called_with("75%")


@pytest.mark.qgis_integration
def test_coverage_opacity_dialog_layer_removed_disables_slider():
    from NoWires.coverage.opacity import CoverageOpacityDialog

    mock_layer = mock.MagicMock()
    mock_layer.id.return_value = "layer_abc"
    mock_layer.name.return_value = "Coverage (1800 MHz)"
    mock_layer.opacity.return_value = 0.6

    dialog = CoverageOpacityDialog(mock_layer)

    with mock.patch.object(dialog, "_resolve_layer", return_value=None):
        dialog._on_slider_changed(50)

        dialog._slider.setEnabled.assert_called_with(False)
        dialog._pct_label.setText.assert_called_with("Layer removed")
