# -*- coding: utf-8 -*-
"""Regression tests for coverage opacity slider feature."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
OPACITY_SOURCE = os.path.join(PLUGIN_DIR, "coverage_opacity.py")
PLUGIN_SOURCE = os.path.join(PLUGIN_DIR, "nowires.py")


def _text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def test_opacity_module_defines_coverage_prefix():
    source = _text(OPACITY_SOURCE)
    assert 'COVERAGE_LAYER_PREFIX = "Coverage ("' in source


def test_opacity_module_has_find_function():
    source = _text(OPACITY_SOURCE)
    assert "def find_latest_coverage_layer():" in source


def test_opacity_module_has_dialog_class():
    source = _text(OPACITY_SOURCE)
    assert "class CoverageOpacityDialog(QDialog):" in source


def test_opacity_dialog_uses_qt_compat_slider_helpers():
    source = _text(OPACITY_SOURCE)
    assert (
        "from .qt_compat import slider_orientation_Horizontal, slider_tick_position_below"
        in source
    )
    assert "slider_orientation_Horizontal(Qt)" in source
    assert "slider_tick_position_below(QSlider)" in source


def test_opacity_dialog_sets_layer_opacity():
    source = _text(OPACITY_SOURCE)
    assert "self._layer.setOpacity(value / 100.0)" in source
    assert "self._layer.triggerRepaint()" in source


def test_opacity_dialog_is_non_modal():
    source = _text(OPACITY_SOURCE)
    assert "self.setModal(False)" in source


def test_opacity_dialog_reads_initial_opacity():
    source = _text(OPACITY_SOURCE)
    assert "layer.opacity()" in source


def test_opacity_dialog_slider_range_is_0_100():
    source = _text(OPACITY_SOURCE)
    assert "self._slider.setRange(0, 100)" in source


def test_opacity_dialog_refreshes_map_canvas():
    source = _text(OPACITY_SOURCE)
    assert "iface.mapCanvas().refresh()" in source


def test_plugin_imports_opacity_module():
    source = _text(PLUGIN_SOURCE)
    assert (
        "from .coverage_opacity import find_latest_coverage_layer, CoverageOpacityDialog"
        in source
    )


def test_plugin_adds_opacity_menu_action():
    source = _text(PLUGIN_SOURCE)
    assert '"Coverage Opacity"' in source
    assert "self.opacity_action" in source
    assert "self.run_coverage_opacity" in source
    assert 'self.iface.addPluginToMenu("&NoWires", self.opacity_action)' in source


def test_plugin_removes_opacity_menu_action_on_unload():
    source = _text(PLUGIN_SOURCE)
    assert 'self.iface.removePluginMenu("&NoWires", self.opacity_action)' in source


def test_plugin_has_coverage_opacity_handler():
    source = _text(PLUGIN_SOURCE)
    assert "def run_coverage_opacity(self):" in source
    assert "find_latest_coverage_layer()" in source
    assert "CoverageOpacityDialog(" in source


def test_plugin_warns_when_no_coverage_layer():
    source = _text(PLUGIN_SOURCE)
    assert "pushWarning(" in source
    assert "No coverage layer found" in source


def test_plugin_tracks_opacity_dialog_reference():
    source = _text(PLUGIN_SOURCE)
    assert "self._opacity_dialog = None" in source
    assert "self._opacity_dialog.close()" in source
