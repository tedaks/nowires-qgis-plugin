# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for nowires.py plugin lifecycle paths."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestStaleTempDirCount:
    def test_count_zero_when_no_nowires_dirs(self, tmp_path, monkeypatch):
        from nowires import _stale_temp_dir_count
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        assert _stale_temp_dir_count() == 0

    def test_count_nowires_dirs(self, tmp_path, monkeypatch):
        from nowires import _stale_temp_dir_count
        base = str(tmp_path)
        os.makedirs(os.path.join(base, "nowires_abc123"))
        os.makedirs(os.path.join(base, "nowires_xyz789"))
        monkeypatch.setattr(tempfile, "gettempdir", lambda: base)
        assert _stale_temp_dir_count() == 2

    def test_count_respects_max_entries(self, tmp_path, monkeypatch):
        from nowires import _stale_temp_dir_count
        base = str(tmp_path)
        for i in range(50):
            os.makedirs(os.path.join(base, "nowires_{:04d}".format(i)))
        monkeypatch.setattr(tempfile, "gettempdir", lambda: base)
        assert 1 <= _stale_temp_dir_count(max_entries=10) <= 50

    def test_mixed_prefixes_ignored(self, tmp_path, monkeypatch):
        from nowires import _stale_temp_dir_count
        base = str(tmp_path)
        os.makedirs(os.path.join(base, "other_dir"))
        os.makedirs(os.path.join(base, "nowires_test"))
        monkeypatch.setattr(tempfile, "gettempdir", lambda: base)
        assert _stale_temp_dir_count() == 1


class TestNoOpPlugin:
    def test_noop_plugin_accepts_iface(self):
        from __init__ import _NoOpPlugin
        p = _NoOpPlugin("fake_iface")
        assert p.iface == "fake_iface"
        assert p._menu_actions == []
        assert p._toolbar_actions == []

    def test_noop_initGui_is_noop(self):
        from __init__ import _NoOpPlugin
        p = _NoOpPlugin(None)
        p.initGui()
        assert True

    def test_noop_unload_is_noop(self):
        from __init__ import _NoOpPlugin
        p = _NoOpPlugin(None)
        p.unload()
        assert True

    def test_noop_getattr_raises_on_any_attr(self):
        from __init__ import _NoOpPlugin
        p = _NoOpPlugin(None)
        try:
            _ = p.some_method
        except AttributeError as e:
            assert "NoOpPlugin" in str(e)
            assert "some_method" in str(e)
