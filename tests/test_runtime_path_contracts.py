# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for persistent QGIS layer backing paths."""

from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent.parent


def _source(name):
    return (PLUGIN_DIR / name).read_text(encoding="utf-8")


def test_dem_merges_use_unique_run_directory_before_returning_layer_path():
    source = _source("dem_downloader.py")
    assert 'tempfile.mkdtemp(prefix="nowires_dem_", dir=temp_dir)' in source
    assert "temp_dir=merge_temp_dir" in source


def test_worldcover_merges_use_unique_run_directory_before_returning_layer_path():
    source = _source("worldcover_downloader.py")
    assert 'tempfile.mkdtemp(prefix="nowires_worldcover_", dir=temp_dir)' in source
    assert "temp_dir=merge_temp_dir" in source

