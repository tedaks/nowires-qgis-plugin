# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for DEM downloader cache path behavior."""

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock


def _import_dem_downloader():
    qgis = types.ModuleType("qgis")
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsGeometry = MagicMock()
    qgis_core.QgsPointXY = MagicMock()
    qgis_core.QgsRectangle = MagicMock()
    sys.modules["qgis"] = qgis
    sys.modules["qgis.core"] = qgis_core
    import os
    plugin_dir = os.path.join(os.path.dirname(__file__), "..")
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)
    no_wires_pkg = types.ModuleType("NoWires")
    no_wires_pkg.__path__ = [plugin_dir]
    no_wires_pkg.__package__ = "NoWires"
    no_wires_pkg.__name__ = "NoWires"
    sys.modules["NoWires"] = no_wires_pkg
    _tile_base = importlib.import_module("tile_download_base")
    sys.modules["NoWires.tile_download_base"] = _tile_base
    setattr(no_wires_pkg, "tile_download_base", _tile_base)
    if "tile_download_base" not in sys.modules:
        sys.modules["tile_download_base"] = _tile_base
    dd = importlib.import_module("NoWires.dem_downloader")
    setattr(no_wires_pkg, "dem_downloader", dd)
    return dd


def test_dem_cache_directory_is_per_user(tmp_path, monkeypatch):
    dd = _import_dem_downloader()

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )

    assert dd.get_temp_dir() == str(tmp_path / "NoWires-alice")


def test_download_tiles_finalizes_download_with_os_replace(tmp_path, monkeypatch):
    dd = _import_dem_downloader()
    tile_name = "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"
    local_tif = tmp_path / (tile_name + ".tif")
    replace_calls = []
    original_replace = dd.os.replace

    class FakeResponse:
        headers = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def geturl(self):
            return "{}{}/{}.tif".format(dd.COPERNICUS_BASE_URL, tile_name, tile_name)

        def read(self, _size):
            if getattr(self, "_read", False):
                return b""
            self._read = True
            return b"good"

    class FakeOpener:
        def open(self, url, timeout):
            return FakeResponse()

    def fake_replace(src, dst):
        replace_calls.append((src, dst))
        original_replace(src, dst)

    monkeypatch.setattr(dd.gdal, "Open", lambda _path: object())
    monkeypatch.setattr(dd.os, "replace", fake_replace)

    paths = dd.download_tiles(
        [tile_name],
        temp_dir=str(tmp_path),
        proxy_opener=FakeOpener(),
    )

    assert paths == [str(local_tif)]
    assert replace_calls == [(str(local_tif) + ".tmp", str(local_tif))]
    assert local_tif.read_bytes() == b"good"
