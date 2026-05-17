# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for hillshade FlushCache (v1.5.7 fix #13).

Source-level contract test: BuildOverviews must be followed by FlushCache
before the dataset handle is released.
"""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "contour_overlay.py"))


def test_hillshade_flush_cache_source_present():
    """contour_overlay.py must call FlushCache() after BuildOverviews."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "FlushCache()" in source, (
        "contour_overlay.py must call FlushCache() on the hillshade dataset "
        "before releasing it"
    )


def test_buildoverviews_followed_by_flushcache():
    """In the source, BuildOverviews must be followed by FlushCache before None."""
    with open(_SOURCE_FILE) as f:
        lines = f.readlines()
    found_build = False
    found_flush_after_build = False
    for i, line in enumerate(lines):
        if "BuildOverviews" in line:
            found_build = True
            # Check that FlushCache appears in subsequent lines before None
            for j in range(i + 1, min(i + 5, len(lines))):
                if "FlushCache" in lines[j]:
                    found_flush_after_build = True
                    break
                if "= None" in lines[j] and "hillshade_ds" in lines[j]:
                    break
    if found_build:
        assert found_flush_after_build, (
            "BuildOverviews must be followed by FlushCache() before hillshade_ds = None"
        )