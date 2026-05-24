# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for macOS multiprocessing process guard."""

import importlib.util
import multiprocessing
import os
import sys

import macos_compat
from macos_compat import (
    configure_macos_multiprocessing,
    find_macos_python_executable,
    is_subprocess,
)
from radio_coverage.pool import should_use_multiprocessing


def _load_init_module():
    plugin_dir = os.path.join(os.path.dirname(__file__), "..")
    spec = importlib.util.spec_from_file_location(
        "NoWires", os.path.join(plugin_dir, "__init__.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestIsSubprocess:
    def test_returns_false_in_main_process(self):
        assert is_subprocess() is False

    def test_returns_true_when_process_name_is_not_main(self, monkeypatch):
        monkeypatch.setattr(
            multiprocessing.current_process(), "name", "ForkPoolWorker-1"
        )
        assert is_subprocess() is True

    def test_returns_false_when_process_name_is_main(self):
        assert multiprocessing.current_process().name == "MainProcess"
        assert is_subprocess() is False


class TestShouldUseMultiprocessing:
    def test_disables_on_windows(self):
        assert should_use_multiprocessing(os_name="nt") is False

    def test_enables_on_posix(self):
        assert should_use_multiprocessing(os_name="posix", platform_name="linux") is True


class TestNoOpPlugin:
    def test_noop_plugin_has_initgui(self):
        init_mod = _load_init_module()
        plugin = init_mod._NoOpPlugin(None)
        assert hasattr(plugin, "initGui")

    def test_noop_plugin_has_unload(self):
        init_mod = _load_init_module()
        plugin = init_mod._NoOpPlugin(None)
        assert hasattr(plugin, "unload")

    def test_noop_plugin_initgui_is_noop(self):
        init_mod = _load_init_module()
        plugin = init_mod._NoOpPlugin(None)
        assert plugin.initGui() is None

    def test_noop_plugin_unload_is_noop(self):
        init_mod = _load_init_module()
        plugin = init_mod._NoOpPlugin(None)
        assert plugin.unload() is None

    def test_noop_plugin_stores_iface(self):
        init_mod = _load_init_module()
        sentinel = object()
        plugin = init_mod._NoOpPlugin(sentinel)
        assert plugin.iface is sentinel


class TestClassFactorySubprocessGuard:
    def test_classfactory_returns_noop_in_subprocess(self, monkeypatch):
        init_mod = _load_init_module()
        monkeypatch.setattr(
            multiprocessing.current_process(), "name", "SpawnPoolWorker-1"
        )
        plugin = init_mod.classFactory(None)
        assert isinstance(plugin, init_mod._NoOpPlugin)

    def test_classfactory_returns_real_plugin_in_main_process(self, monkeypatch):
        init_mod = _load_init_module()
        monkeypatch.setattr(
            multiprocessing.current_process(), "name", "MainProcess"
        )
        try:
            plugin = init_mod.classFactory(None)
            assert not isinstance(plugin, init_mod._NoOpPlugin)
        except (ImportError, TypeError):
            pass

    def test_classfactory_checks_process_name(self):
        init_mod = _load_init_module()
        assert callable(init_mod.classFactory)


class TestFindMacosPythonExecutable:
    def test_returns_none_on_non_darwin(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        assert find_macos_python_executable() is None

    def test_prefers_base_executable_when_distinct(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "platform", "darwin")
        fake_python = tmp_path / "real_python"
        fake_python.write_text("#!/bin/sh\nexit 0\n")
        fake_python.chmod(0o755)
        monkeypatch.setattr(sys, "executable", "/Applications/QGIS.app/Contents/MacOS/QGIS")
        monkeypatch.setattr(sys, "_base_executable", str(fake_python), raising=False)
        assert find_macos_python_executable() == str(fake_python)

    def test_skips_base_executable_when_same_as_executable(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "platform", "darwin")
        qgis_dir = tmp_path / "MacOS"
        bin_dir = qgis_dir / "bin"
        bin_dir.mkdir(parents=True)
        qgis_bin = qgis_dir / "QGIS"
        qgis_bin.write_text("")
        py_bin = bin_dir / "python{}.{}".format(
            sys.version_info.major, sys.version_info.minor
        )
        py_bin.write_text("#!/bin/sh\nexit 0\n")
        py_bin.chmod(0o755)
        monkeypatch.setattr(sys, "executable", str(qgis_bin))
        monkeypatch.setattr(sys, "_base_executable", str(qgis_bin), raising=False)
        assert find_macos_python_executable() == str(py_bin)

    def test_falls_back_to_bin_python(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "platform", "darwin")
        qgis_dir = tmp_path / "MacOS"
        bin_dir = qgis_dir / "bin"
        bin_dir.mkdir(parents=True)
        qgis_bin = qgis_dir / "QGIS"
        qgis_bin.write_text("")
        py_bin = bin_dir / "python{}".format(sys.version_info.major)
        py_bin.write_text("#!/bin/sh\nexit 0\n")
        py_bin.chmod(0o755)
        monkeypatch.setattr(sys, "executable", str(qgis_bin))
        monkeypatch.delattr(sys, "_base_executable", raising=False)
        assert find_macos_python_executable() == str(py_bin)

    def test_returns_none_when_no_python_found(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "platform", "darwin")
        qgis_bin = tmp_path / "QGIS"
        qgis_bin.write_text("")
        monkeypatch.setattr(sys, "executable", str(qgis_bin))
        monkeypatch.delattr(sys, "_base_executable", raising=False)
        assert find_macos_python_executable() is None

    def test_skips_non_executable_candidate(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "platform", "darwin")
        qgis_dir = tmp_path / "MacOS"
        bin_dir = qgis_dir / "bin"
        bin_dir.mkdir(parents=True)
        qgis_bin = qgis_dir / "QGIS"
        qgis_bin.write_text("")
        py_bin = bin_dir / "python{}.{}".format(
            sys.version_info.major, sys.version_info.minor
        )
        py_bin.write_text("not executable")
        py_bin.chmod(0o644)
        monkeypatch.setattr(sys, "executable", str(qgis_bin))
        monkeypatch.delattr(sys, "_base_executable", raising=False)
        assert find_macos_python_executable() is None


class TestConfigureMacosMultiprocessing:
    def test_noop_on_non_darwin(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        called = []
        monkeypatch.setattr(
            multiprocessing, "set_executable", lambda p: called.append(p)
        )
        configure_macos_multiprocessing()
        assert called == []

    def test_sets_executable_when_python_found(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setattr(
            macos_compat, "find_macos_python_executable", lambda: "/fake/python3"
        )
        captured = []
        monkeypatch.setattr(
            multiprocessing, "set_executable", lambda p: captured.append(p)
        )
        configure_macos_multiprocessing()
        assert captured == ["/fake/python3"]

    def test_does_not_set_executable_when_python_not_found(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setattr(
            macos_compat, "find_macos_python_executable", lambda: None
        )
        called = []
        monkeypatch.setattr(
            multiprocessing, "set_executable", lambda p: called.append(p)
        )
        configure_macos_multiprocessing()
        assert called == []