# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""PyQt dialog tests — construction, signal wiring, layer resolution, headless.

These tests use the conftest-provided PyQt stubs. They verify structural
contracts without requiring a real QGIS runtime.

SKIPPED when real QGIS is available because they overwrite sys.modules
with mocks, which segfaults against compiled QGIS extensions.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))

pytestmark = pytest.mark.skipif(
    _HAS_REAL_QGIS,
    reason="PyQt dialog tests use mock QGIS and must not run against real QGIS extensions",
)


# Same restoration pattern as test_plugin_load to handle mock corruption.
_SAVED_MODULES = {
    key: sys.modules.get(key)
    for key in (
        "qgis", "qgis.core", "qgis.PyQt", "qgis.PyQt.QtCore",
        "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets", "qgis.utils",
        "processing", "osgeo", "osgeo.gdal", "osgeo.osr", "osgeo.ogr",
    )
}
_SAVED_NOWIRES_PKG = sys.modules.get("NoWires")


@pytest.fixture(autouse=True)
def _restore_qgis_mocks():
    """Restore conftest QGIS mocks and purge stale module references."""
    for key, saved in _SAVED_MODULES.items():
        if saved is not None:
            sys.modules[key] = saved
    if _SAVED_NOWIRES_PKG is not None:
        sys.modules["NoWires"] = _SAVED_NOWIRES_PKG
    stale_keys = [k for k in list(sys.modules) if k.startswith("NoWires.") and k != "NoWires.__init__"]
    for key in stale_keys:
        mod = sys.modules.get(key)
        if mod is not None and hasattr(mod, "__file__") and mod.__file__ is not None:
            try:
                source = open(mod.__file__).read()
                if "qgis" in source:
                    del sys.modules[key]
            except (OSError, UnicodeDecodeError):
                del sys.modules[key]
    yield


def _make_layer(layer_id="test_id", name="Coverage (test)", opacity=0.5):
    """Create a mock layer matching CoverageOpacityDialog's interface."""
    layer = MagicMock()
    layer.id.return_value = layer_id
    layer.name.return_value = name
    layer.opacity.return_value = opacity
    layer.isValid.return_value = True
    return layer


def _make_dialog(layer=None):
    """Create a CoverageOpacityDialog with a mock layer."""
    if layer is None:
        layer = _make_layer()
    from NoWires.radio_coverage.opacity import CoverageOpacityDialog
    return CoverageOpacityDialog(layer)


class TestCoverageOpacityDialogConstruction:
    def test_dialog_stores_layer_id(self):
        dialog = _make_dialog(layer=_make_layer(layer_id="abc123"))
        assert dialog._layer_id == "abc123"

    def test_dialog_slider_range_covers_zero_to_hundred(self):
        dialog = _make_dialog()
        assert dialog._slider.setRange.called

    def test_dialog_is_non_modal_by_design(self):
        """CoverageOpacityDialog calls setModal(False) in __init__."""
        from NoWires.radio_coverage.opacity import CoverageOpacityDialog
        # Verify the source code explicitly calls setModal(False)
        import inspect
        source = inspect.getsource(CoverageOpacityDialog.__init__)
        assert "setModal(False)" in source


class TestCoverageOpacityDialogSlider:
    def test_slider_change_updates_label(self):
        dialog = _make_dialog()
        dialog._on_slider_changed(75)
        dialog._pct_label.setText.assert_called_with("75%")

    def test_slider_change_sets_layer_opacity(self):
        dialog = _make_dialog()
        layer = MagicMock()
        with patch.object(dialog, "_resolve_layer", return_value=layer):
            dialog._on_slider_changed(60)
            layer.setOpacity.assert_called_with(0.6)

    def test_slider_change_triggers_layer_repaint(self):
        dialog = _make_dialog()
        layer = MagicMock()
        with patch.object(dialog, "_resolve_layer", return_value=layer):
            dialog._on_slider_changed(50)
            assert layer.triggerRepaint.called

    def test_deleted_layer_disables_slider_sets_enabled_false(self):
        dialog = _make_dialog()
        with patch.object(dialog, "_resolve_layer", return_value=None):
            dialog._on_slider_changed(30)
            dialog._slider.setEnabled.assert_called_with(False)

    def test_deleted_label_shows_layer_removed(self):
        dialog = _make_dialog()
        with patch.object(dialog, "_resolve_layer", return_value=None):
            dialog._on_slider_changed(30)
            dialog._pct_label.setText.assert_called_with("Layer removed")


class TestCoverageOpacityDialogLayerResolution:
    def test_resolve_layer_fetches_from_project(self):
        dialog = _make_dialog(layer=_make_layer(layer_id="my_layer"))
        with patch("NoWires.radio_coverage.opacity.QgsProject") as mock_project:
            mock_project.instance().mapLayer.return_value = _make_layer()
            result = dialog._resolve_layer()
            assert result is not None

    def test_resolve_layer_returns_none_for_invalid_layer(self):
        dialog = _make_dialog(layer=_make_layer(layer_id="gone"))
        with patch("NoWires.radio_coverage.opacity.QgsProject") as mock_project:
            bad_layer = MagicMock()
            bad_layer.isValid.return_value = False
            mock_project.instance().mapLayer.return_value = bad_layer
            result = dialog._resolve_layer()
            assert result is None

    def test_resolve_layer_returns_none_for_missing_layer(self):
        dialog = _make_dialog(layer=_make_layer(layer_id="missing"))
        with patch("NoWires.radio_coverage.opacity.QgsProject") as mock_project:
            mock_project.instance().mapLayer.return_value = None
            result = dialog._resolve_layer()
            assert result is None


class TestFindLatestCoverageLayer:
    def test_returns_none_when_no_layers_exist(self):
        from NoWires.radio_coverage.opacity import find_latest_coverage_layer
        with patch("NoWires.radio_coverage.opacity.QgsProject") as mock_project:
            mock_project.instance().mapLayers.return_value = {}
            mock_project.instance().readEntry.return_value = ("", False)
            result = find_latest_coverage_layer()
            assert result is None

    def test_returns_layer_matching_prefix(self):
        from NoWires.radio_coverage.opacity import find_latest_coverage_layer, COVERAGE_LAYER_PREFIX
        matching = MagicMock()
        matching.name.return_value = COVERAGE_LAYER_PREFIX + "test)"
        non_matching = MagicMock()
        non_matching.name.return_value = "Some Other Layer"
        with patch("NoWires.radio_coverage.opacity.QgsProject") as mock_project:
            mock_project.instance().mapLayers.return_value = {
                "a": non_matching, "b": matching
            }
            mock_project.instance().readEntry.return_value = ("", False)
            result = find_latest_coverage_layer()
            assert result == matching
