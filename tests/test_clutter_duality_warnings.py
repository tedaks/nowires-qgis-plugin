# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: simple-mode clutter warnings must be accurate per v1.6.6."""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_ENGINE_PATH = os.path.join(_HERE, "..", "radio_coverage", "engine.py")


def test_engine_warnings_removed_misleading_ignored():
    with open(_ENGINE_PATH, encoding="utf-8") as f:
        source = f.read()
    assert "BEL_ENABLED=True ignored" not in source
    assert "TX_CLUTTER_OVERRIDE=%s ignored" not in source


def test_engine_warning_for_percentile_is_accurate():
    with open(_ENGINE_PATH, encoding="utf-8") as f:
        source = f.read()
    assert "CLUTTER_PERCENTILE" in source
    assert "only affects BEL" in source
