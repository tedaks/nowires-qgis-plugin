# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression tests for NoWires 3D support wiring."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
THREE_D_SOURCE = os.path.join(PLUGIN_DIR, "three_d.py")
PLUGIN_SOURCE = os.path.join(PLUGIN_DIR, "nowires.py")


def _text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def test_three_d_module_exposes_scene_launcher_and_layer_helpers():
    source = _text(THREE_D_SOURCE)
    assert "def remember_nowires_3d_layers(" in source
    assert "def resolve_nowires_3d_layers(" in source
    assert "def open_nowires_3d_view(" in source
    assert 'SCENE_MODE_LOCAL = "local"' in source
    assert 'SCENE_MODE_GLOBE = "globe"' in source


def test_three_d_module_uses_unified_nowires_project_keys():
    source = _text(THREE_D_SOURCE)
    assert 'PROJECT_SCOPE = "NoWires"' in source
    assert "ENTRY_KEY_LAST_COVERAGE" in source
    assert "ENTRY_KEY_LAST_DEM" in source


def test_three_d_module_generates_unique_view_names():
    source = _text(THREE_D_SOURCE)
    assert "mapCanvases3D()" in source
    assert "NoWires 3D View" in source


def test_three_d_module_guards_windows_canvas_creation():
    source = _text(THREE_D_SOURCE)
    assert 'sys.platform == "win32"' in source
    assert "View > 3D Map Views > New 3D Map View" in source


def test_three_d_module_windows_warning_mentions_native_menu_and_dem():
    source = _text(THREE_D_SOURCE)
    assert "NoWires DEM" in source
    assert "terrain" in source
    assert "highlight" in source.lower()


def test_three_d_windows_fallback_uses_clicked_button_and_checked_default():
    source = _text(THREE_D_SOURCE)
    assert "cb.setChecked(True)" in source
    assert "dialog.clickedButton()" in source
    assert "dialog.highlight_button" in source


def test_plugin_adds_open_3d_view_action():
    source = _text(PLUGIN_SOURCE)
    assert '"Open 3D View"' in source
    assert "self.run_open_3d_view" in source
    assert "self.iface.addPluginMenu" not in source
    assert "_MENU_NAME" in source


def test_plugin_removes_open_3d_view_action_on_unload():
    source = _text(PLUGIN_SOURCE)
    assert "_MENU_NAME" in source


def test_plugin_uses_three_d_helper_for_launcher():
    source = _text(PLUGIN_SOURCE)
    assert "open_nowires_3d_view" in source
    assert "QInputDialog.getItem(" in source
    assert "QTimer.singleShot(" in source


def test_remember_callers_exist_in_algorithm_files():
    for filename in ("algorithm/_coverage_helpers.py", "p2p/compute.py"):
        path = os.path.join(PLUGIN_DIR, filename)
        source = _text(path)
        assert "remember_nowires_3d_layers" in source, \
            "missing remember_nowires_3d_layers call in {}".format(filename)
