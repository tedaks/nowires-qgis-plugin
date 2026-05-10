# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for DEM downloader cache path behavior."""

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock


_dd = None
_tile_base = None


def _import_dem_downloader():
    global _dd, _tile_base
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
    _gdal_mock = MagicMock()
    sys.modules.setdefault("osgeo.gdal", _gdal_mock)
    sys.modules.setdefault("osgeo", MagicMock())
    sys.modules.setdefault("osgeo.ogr", MagicMock())
    sys.modules.setdefault("osgeo.osr", MagicMock())
    _dd = importlib.import_module("NoWires.dem_downloader")
    setattr(no_wires_pkg, "dem_downloader", _dd)
    return _dd


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


def test_dem_cache_directory_sanitizes_username(tmp_path, monkeypatch):
    dd = _import_dem_downloader()

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "ali ce:bad/name"),
        raising=False,
    )

    assert dd.get_temp_dir() == str(tmp_path / "NoWires-ali_ce_bad_name")


def test_dem_cache_directory_uses_default_username_when_lookup_fails(
    tmp_path, monkeypatch
):
    dd = _import_dem_downloader()

    def getuser_raises():
        raise OSError("no user")

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=getuser_raises),
        raising=False,
    )

    assert dd.get_temp_dir() == str(tmp_path / "NoWires-nowires")


def test_dem_cache_directory_replaces_existing_file(tmp_path, monkeypatch):
    dd = _import_dem_downloader()
    target = tmp_path / "NoWires-alice"
    target.write_text("not a directory", encoding="utf-8")

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )

    assert dd.get_temp_dir() == str(target)
    assert target.is_dir()


def test_dem_cache_directory_validates_existing_dir_with_nofollow_flags(
    tmp_path, monkeypatch
):
    dd = _import_dem_downloader()
    target = tmp_path / "NoWires-alice"
    target.mkdir()
    calls = []

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.setattr(dd.os, "O_DIRECTORY", 0x10000, raising=False)
    monkeypatch.setattr(dd.os, "O_NOFOLLOW", 0x20000, raising=False)
    monkeypatch.setattr(dd.os, "open", lambda path, flags: calls.append((path, flags)) or 42)
    monkeypatch.setattr(dd.os, "close", lambda fd: calls.append(("close", fd)))

    assert dd.get_temp_dir() == str(target)
    assert calls == [
        (str(target), dd.os.O_RDONLY | dd.os.O_DIRECTORY | dd.os.O_NOFOLLOW),
        ("close", 42),
    ]


def test_dem_cache_directory_handles_platforms_without_nofollow_flags(tmp_path, monkeypatch):
    dd = _import_dem_downloader()
    target = tmp_path / "NoWires-alice"
    target.mkdir()

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.delattr(dd.os, "O_DIRECTORY", raising=False)
    monkeypatch.delattr(dd.os, "O_NOFOLLOW", raising=False)

    assert dd.get_temp_dir() == str(target)


def test_dem_cache_directory_uses_fallback_path_when_rename_fails(
    tmp_path, monkeypatch
):
    dd = _import_dem_downloader()
    target = tmp_path / "NoWires-alice"

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.setattr(
        dd.os,
        "rename",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("rename failed")),
    )

    result = dd.get_temp_dir()

    assert result != str(target)
    assert result.startswith(str(tmp_path / "NoWires-"))
    assert dd.os.path.isdir(result)


def test_dem_cache_directory_does_not_crash_when_existing_dir_open_fails(
    tmp_path, monkeypatch
):
    dd = _import_dem_downloader()
    target = tmp_path / "NoWires-alice"
    target.mkdir()

    monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        dd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.setattr(dd.os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        OSError("simulated directory open failure")
    ))

    assert dd.get_temp_dir() == str(target)


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

    monkeypatch.setattr(_tile_base.gdal, "Open", lambda _path: object())
    monkeypatch.setattr(dd.os, "replace", fake_replace)

    paths = dd.download_tiles(
        [tile_name],
        temp_dir=str(tmp_path),
        proxy_opener=FakeOpener(),
    )

    assert paths == [str(local_tif)]
    assert replace_calls == [(str(local_tif) + ".tmp", str(local_tif))]
    assert local_tif.read_bytes() == b"good"
