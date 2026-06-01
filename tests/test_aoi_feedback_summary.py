# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: ensure_dem_for_area must push AOI summary before downloading.

The v1.7.1 pre-run feedback gives the user a quick summary (AOI span, tile
count, estimated size, pixel count) before the blocking DEM download.
"""

import os

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_ensure_dem_provides_aoi_summary():
    src = _source("dem_downloader.py")
    assert "feedback.pushInfo" in src
    assert "\u00b0" in src or "AOI" in src


def test_summary_before_download():
    src = _source("dem_downloader.py")
    ensure_pos = src.find("def ensure_dem_for_area")
    assert ensure_pos != -1
    after_ensure = src[ensure_pos:]
    summary_pos = after_ensure.find('"AOI ')
    tiles_call_pos = after_ensure.find("tile_paths = download_tiles(")
    assert summary_pos != -1, "must have an AOI summary in ensure_dem_for_area"
    assert tiles_call_pos != -1
    assert summary_pos < tiles_call_pos, "AOI summary must appear before download_tiles call"