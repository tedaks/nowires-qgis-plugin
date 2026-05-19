# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for temp-dir leak in ContourLinesAlgorithm (v1.5.7 fix #14).

Source-level contract tests: when get_temp_dir() returns None, the fallback
tempfile.mkdtemp must be registered with TempDirManager.add_dir() for cleanup.
"""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "algorithm/contour.py"))


def test_contour_init_routes_fallback_through_tmp_manager():
    """The fallback tempfile.mkdtemp must be registered with TempDirManager."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "self._tmp.add_dir(self.temp_dir)" in source, (
        "The fallback tempfile.mkdtemp() result must be registered with "
        "self._tmp.add_dir() so it's cleaned up in the finally block"
    )


def test_contour_no_never_cleaned_comment():
    """The old 'never cleaned' comment must be removed."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "never cleaned" not in source.lower(), (
        "The old 'never cleaned' comment on the fallback temp dir must be "
        "removed now that the fallback is registered with TempDirManager"
    )