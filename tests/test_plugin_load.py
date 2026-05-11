# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Plugin lifecycle tests — classFactory, initGui, unload — using mocked QGIS.

These tests must restore QGIS mock modules because some other test files
overwrite sys.modules["qgis.core"] with their own stub implementations
and don't restore them, breaking our mock state.

SKIPPED when real QGIS is available because they overwrite sys.modules
with mocks, which segfaults against compiled QGIS extensions.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))


# Preserve the conftest-provided mock modules before any other test overwrites them.
_SAVED_MODULES = {
    key: sys.modules.get(key)
    for key in (
        "qgis", "qgis.core", "qgis.PyQt", "qgis.PyQt.QtCore",
        "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets", "qgis.utils",
        "processing", "osgeo", "osgeo.gdal", "osgeo.osr", "osgeo.ogr",
    )
}

# Also preserve the NoWires package itself so we can restore it.
_SAVED_NOWIRES_PKG = sys.modules.get("NoWires")

pytestmark = pytest.mark.skipif(
    _HAS_REAL_QGIS,
    reason="Plugin lifecycle tests use mock QGIS and must not run against real QGIS extensions",
)


@pytest.fixture(autouse=True)
def _restore_qgis_mocks():
    """Restore conftest QGIS mocks and purge stale NoWires module references.

    Some test files overwrite sys.modules["qgis.core"] etc. with their own
    stub implementations (e.g. test_review_fixes). When those tests import
    NoWires submodules, classes like NoWiresProvider inherit from the
    overwritten mock. Simply restoring sys.modules is not enough — the class
    __bases__ are already set. We must also purge all NoWires.* submodules
    that cached wrong QGIS references so they get re-imported fresh.
    """
    # 1. Restore conftest mocks in sys.modules
    for key, saved in _SAVED_MODULES.items():
        if saved is not None:
            sys.modules[key] = saved

    # 2. Restore the NoWires package stub.
    if _SAVED_NOWIRES_PKG is not None:
        sys.modules["NoWires"] = _SAVED_NOWIRES_PKG

    # 3. Purge all NoWires.* submodules that may have cached references to
    #    the wrong QGIS mocks. They will be re-imported on next access,
    #    picking up the restored conftest mocks.
    stale_keys = [k for k in list(sys.modules) if k.startswith("NoWires.") and k != "NoWires.__init__"]
    for key in stale_keys:
        # Don't purge pure-compute modules that don't import qgis
        # (like antenna, radio, etc.) — they're safe to keep cached.
        # Only purge modules that import from qgis.
        mod = sys.modules.get(key)
        if mod is not None and hasattr(mod, "__file__") and mod.__file__ is not None:
            try:
                source = open(mod.__file__).read()
                if "qgis" in source:
                    del sys.modules[key]
            except (OSError, UnicodeDecodeError):
                del sys.modules[key]

    yield


def _make_iface():
    """Minimal iface stub matching the QGIS iface contract used by NoWires."""
    iface = MagicMock()
    iface.mainWindow.return_value = MagicMock()
    iface.mapCanvas.return_value = MagicMock()
    iface.messageBar.return_value = MagicMock()
    iface.addPluginToMenu = MagicMock()
    iface.removePluginMenu = MagicMock()
    iface.addToolBarIcon = MagicMock()
    iface.removeToolBarIcon = MagicMock()
    return iface


def _make_registry():
    """Create a mock processing registry."""
    return MagicMock()


class TestClassFactory:
    def test_returns_plugin_instance_in_main_process(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "MainProcess"})()
        )
        from NoWires import classFactory
        plugin = classFactory(_make_iface())
        assert hasattr(plugin, "initGui")
        assert hasattr(plugin, "unload")

    def test_returns_noop_plugin_in_subprocess(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "PoolWorker-1"})()
        )
        from NoWires import classFactory
        plugin = classFactory(_make_iface())
        assert plugin.__class__.__name__ == "_NoOpPlugin"

    def test_noop_plugin_initgui_is_noop(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "PoolWorker-1"})()
        )
        from NoWires import classFactory
        plugin = classFactory(_make_iface())
        plugin.initGui()  # should not raise

    def test_noop_plugin_unload_is_noop(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "PoolWorker-1"})()
        )
        from NoWires import classFactory
        plugin = classFactory(_make_iface())
        plugin.unload()  # should not raise

    def test_noop_plugin_getattr_raises_attribute_error(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "PoolWorker-1"})()
        )
        from NoWires import classFactory
        plugin = classFactory(_make_iface())
        with pytest.raises(AttributeError):
            plugin.nonexistent_method


class TestPluginInitGui:
    def test_init_gui_registers_provider(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "MainProcess"})()
        )
        mock_registry = _make_registry()
        with patch("NoWires.nowires.QgsApplication") as MockApp:
            MockApp.processingRegistry.return_value = mock_registry
            from NoWires import classFactory
            plugin = classFactory(_make_iface())
            plugin.initGui()
            assert mock_registry.addProvider.called

    def test_init_gui_creates_menu_actions(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "MainProcess"})()
        )
        mock_registry = _make_registry()
        with patch("NoWires.nowires.QgsApplication") as MockApp:
            MockApp.processingRegistry.return_value = mock_registry
            from NoWires import classFactory
            plugin = classFactory(_make_iface())
            plugin.initGui()
            assert len(plugin._menu_actions) > 0

    def test_init_gui_creates_toolbar_actions(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "MainProcess"})()
        )
        mock_registry = _make_registry()
        with patch("NoWires.nowires.QgsApplication") as MockApp:
            MockApp.processingRegistry.return_value = mock_registry
            from NoWires import classFactory
            plugin = classFactory(_make_iface())
            plugin.initGui()
            assert len(plugin._toolbar_actions) >= 2


class TestPluginUnload:
    def test_unload_removes_provider(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "MainProcess"})()
        )
        mock_registry = _make_registry()
        with patch("NoWires.nowires.QgsApplication") as MockApp:
            MockApp.processingRegistry.return_value = mock_registry
            from NoWires import classFactory
            plugin = classFactory(_make_iface())
            plugin.initGui()
            plugin.unload()
            assert mock_registry.removeProvider.called

    def test_unload_clears_provider_reference(self, monkeypatch):
        monkeypatch.setattr(
            "multiprocessing.current_process",
            lambda: type("Proc", (), {"name": "MainProcess"})()
        )
        mock_registry = _make_registry()
        with patch("NoWires.nowires.QgsApplication") as MockApp:
            MockApp.processingRegistry.return_value = mock_registry
            from NoWires import classFactory
            plugin = classFactory(_make_iface())
            plugin.initGui()
            plugin.unload()
            assert plugin.provider is None
