# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for removal of the overall wall-clock deadline.

The per-tile wall-clock budget (DEFAULT_PER_TILE_WALL_CLOCK_BUDGET = 180s) in
tile_download_base.download_tile_with_retry already caps runaway downloads
per tile. The old overall-deadline (_WALL_CLOCK_TIMEOUT) in
dem_downloader.download_tiles and worldcover_downloader.download_tiles did not
scale with tile count, so legitimately-large coverage areas could false-trip
the timeout even when each individual tile was downloading at a healthy rate.
The overall deadline has been removed.
"""

import os
from unittest.mock import MagicMock


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)


def _read_source(filename):
    path = os.path.normpath(os.path.join(_PLUGIN_DIR, filename))
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_dem_downloader_has_no_wall_clock_timeout_constant():
    """dem_downloader must not define an overall-deadline constant."""
    src = _read_source("dem_downloader.py")
    assert "_WALL_CLOCK_TIMEOUT" not in src, (
        "dem_downloader._WALL_CLOCK_TIMEOUT must be removed; "
        "per-tile budget in tile_download_base covers runaway protection"
    )


def test_worldcover_downloader_has_no_wall_clock_timeout_constant():
    """worldcover_downloader must not define an overall-deadline constant."""
    src = _read_source("worldcover_downloader.py")
    assert "_WALL_CLOCK_TIMEOUT" not in src, (
        "worldcover_downloader._WALL_CLOCK_TIMEOUT must be removed; "
        "per-tile budget in tile_download_base covers runaway protection"
    )


def test_dem_downloader_has_no_deadline_check():
    """dem_downloader.download_tiles must not check a deadline."""
    src = _read_source("dem_downloader.py")
    assert "deadline" not in src, (
        "dem_downloader must not reference a deadline; "
        "downloads run until each tile completes or the per-tile budget fires"
    )


def test_worldcover_downloader_has_no_deadline_check():
    """worldcover_downloader.download_tiles must not check a deadline."""
    src = _read_source("worldcover_downloader.py")
    assert "deadline" not in src, (
        "worldcover_downloader must not reference a deadline; "
        "downloads run until each tile completes or the per-tile budget fires"
    )


def test_dem_download_tiles_processes_all_tiles_for_large_request(
    tmp_path, monkeypatch
):
    """A large tile list completes every tile; no overall timeout."""
    import dem_downloader as dd

    monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))

    visited = []

    def _fake_retry(tile_url, local_tif, base_name_label, **_kwargs):
        visited.append(base_name_label)
        return local_tif

    monkeypatch.setattr(dd, "download_tile_with_retry", _fake_retry)

    tile_names = ["tile_{:03d}".format(i) for i in range(50)]
    paths = dd.download_tiles(tile_names, temp_dir=str(tmp_path))

    assert len(paths) == 50
    assert visited == tile_names


def test_worldcover_download_tiles_processes_all_tiles_for_large_request(
    tmp_path, monkeypatch
):
    """A large WorldCover tile list completes every tile; no overall timeout."""
    import worldcover_downloader as wd

    monkeypatch.setattr(wd, "get_worldcover_dir", lambda: str(tmp_path))

    visited = []

    def _fake_retry(tile_url, local_tif, base_name_label, **_kwargs):
        visited.append(base_name_label)
        return local_tif

    monkeypatch.setattr(wd, "download_tile_with_retry", _fake_retry)

    tile_names = ["ESA_WorldCover_{:03d}".format(i) for i in range(50)]
    feedback = MagicMock()
    feedback.isCanceled.return_value = False
    paths = wd.download_worldcover_tiles(
        tile_names, temp_dir=str(tmp_path), feedback=feedback
    )

    assert len(paths) == 50
    assert visited == tile_names
