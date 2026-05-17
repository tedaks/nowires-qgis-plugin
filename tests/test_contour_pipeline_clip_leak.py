# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for GDAL dataset leak in download_and_merge_tiles (v1.5.7 fix #9).

Source-level contract test: the clip-check gdal.Open must assign its
result to a variable and release it explicitly, not use bare gdal.Open()
which leaks a dataset handle.
"""

import ast
import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "contour_pipeline.py"))


def test_gdal_open_clip_check_releases_dataset():
    """The clip-check gdal.Open result must be assigned and released.
    
    Before v1.5.7, ``if gdal.Open(fn_clip) is None: continue`` leaked
    a GDAL dataset handle because the opened dataset was never explicitly
    released. The fix assigns to test_ds and sets test_ds = None.
    """
    with open(_SOURCE_FILE) as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            cond = node.test
            if (isinstance(cond, ast.Compare)
                    and isinstance(cond.left, ast.Call)
                    and isinstance(cond.left.func, ast.Attribute)):
                if (cond.left.func.attr == "Open"
                        and isinstance(cond.left.func.value, ast.Name)
                        and cond.left.func.value.id == "gdal"):
                    assert isinstance(cond.left, ast.Name), (
                        "gdal.Open() in clip-check must be assigned to a "
                        "variable so it can be explicitly released; bare "
                        "gdal.Open(fn_clip) is None leaks the dataset handle"
                    )


def test_source_has_explicit_release_after_clip_check():
    """contour_pipeline.py must have ``test_ds = None`` after the clip check."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "test_ds = None" in source, (
        "clip-check must explicitly release GDAL dataset with 'test_ds = None'"
    )