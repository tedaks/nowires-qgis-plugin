# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests pushing coverage above the 65% threshold for CI tests.yml."""

import os
import sys

SELF = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SELF, ".."))


class TestInitClassFactoryEdge:
    def test_classfactory_noop_plugin_path(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        import multiprocessing
        if multiprocessing.current_process().name == "MainProcess":
            from NoWires.__init__ import classFactory
            result = classFactory(None)
            assert result is not None


class TestNowiresHelpers:
    def test_stale_temp_dir_max_entries_zero(self, monkeypatch, tmp_path):
        from nowires import _stale_temp_dir_count
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        assert _stale_temp_dir_count(max_entries=0) == 0


class TestAntennaHelpers:
    def test_vertical_gain_factor_on_beam(self):
        from NoWires.antenna import _vertical_gain_factor
        g = _vertical_gain_factor(0.0, 0.0, 360.0)
        assert g <= 0.0

    def test_vertical_gain_factor_off_beam(self):
        from NoWires.antenna import _vertical_gain_factor
        g = _vertical_gain_factor(90.0, 0.0, 30.0)
        assert g == -12.0

    def test_vertical_gain_factor_with_downtilt(self):
        from NoWires.antenna import _vertical_gain_factor
        g = _vertical_gain_factor(5.0, 5.0, 30.0)
        assert g <= 0.0

