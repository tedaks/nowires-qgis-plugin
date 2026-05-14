# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for dem_downloader.py — timeout, cancel, and orchestration paths."""

import importlib
import math
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


def _import_dem_downloader():
    import importlib.util as _ilu

    plugin_dir = os.path.join(os.path.dirname(__file__), "..")

    qgis = types.ModuleType("qgis")
    qgis_core = types.ModuleType("qgis.core")
    qgis_core.QgsGeometry = MagicMock()
    qgis_core.QgsPointXY = MagicMock()
    qgis_core.QgsRectangle = MagicMock()
    if "qgis" not in sys.modules:
        sys.modules["qgis"] = qgis
    if "qgis.core" not in sys.modules:
        sys.modules["qgis.core"] = qgis_core

    if "NoWires" in sys.modules:
        no_wires_pkg = sys.modules["NoWires"]
    else:
        no_wires_pkg = types.ModuleType("NoWires")
        no_wires_pkg.__path__ = [plugin_dir]
        no_wires_pkg.__package__ = "NoWires"
        no_wires_pkg.__name__ = "NoWires"
        sys.modules["NoWires"] = no_wires_pkg

    tb = importlib.import_module("tile_download_base")
    sys.modules["NoWires.tile_download_base"] = tb
    setattr(no_wires_pkg, "tile_download_base", tb)
    if "tile_download_base" not in sys.modules:
        sys.modules["tile_download_base"] = tb

    _gdal_mock = MagicMock()
    sys.modules.setdefault("osgeo.gdal", _gdal_mock)
    sys.modules.setdefault("osgeo", MagicMock())
    sys.modules.setdefault("osgeo.ogr", MagicMock())
    sys.modules.setdefault("osgeo.osr", MagicMock())

    spec = _ilu.spec_from_file_location(
        "NoWires.dem_downloader",
        os.path.join(plugin_dir, "dem_downloader.py"),
        submodule_search_locations=[plugin_dir],
    )
    dd = _ilu.module_from_spec(spec)
    sys.modules["NoWires.dem_downloader"] = dd
    setattr(no_wires_pkg, "dem_downloader", dd)
    spec.loader.exec_module(dd)
    return dd, tb


class _Feedback:
    def __init__(self, canceled=False):
        self.messages = []
        self._canceled = canceled
    def pushInfo(self, m):
        self.messages.append(m)
    def isCanceled(self):
        return self._canceled


class FakeResponse:
    def __init__(self, url, chunks, headers=None):
        self._url = url
        self._chunks = list(chunks)
        self.headers = headers or {}
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def geturl(self):
        return self._url
    def read(self, _size):
        if self._chunks:
            return self._chunks.pop(0)
        return b""


class FakeOpener:
    def __init__(self, response=None):
        self.response = response or FakeResponse("https://example.test/tile.tif", [b"ok"],
                                                   {"Content-Length": "2"})
    def open(self, url, timeout):
        return self.response


class TestDownloadTilesTimeoutAndCancel:
    def test_download_tiles_respects_feedback_cancel(self, tmp_path, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))

        class _CancelFeed:
            def isCanceled(self):
                return True
            def pushInfo(self, _m):
                pass

        paths = dd.download_tiles(
            ["N00E000"],
            temp_dir=str(tmp_path),
            feedback=_CancelFeed(),
        )
        assert paths == []

    def test_download_tiles_wall_clock_exceeded(self, tmp_path, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))
        monkeypatch.setattr(dd, "_WALL_CLOCK_TIMEOUT", 0)

        paths = dd.download_tiles(
            ["N00E000"],
            temp_dir=str(tmp_path),
        )
        assert paths == []


class TestEnsureDEMForArea:
    def test_no_tiles_returns_none(self, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: "/tmp/nowires_test")

        def _no_tiles(*a, **kw):
            return []

        monkeypatch.setattr(dd, "required_tiles", _no_tiles)

        result = dd.ensure_dem_for_area(0.0, 1.0, 0.0, 1.0)
        assert result is None

    def test_single_tile_returned_directly(self, tmp_path, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        tile_name = "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))

        monkeypatch.setattr(dd, "required_tiles", lambda *a, **kw: [tile_name])

        def _download(tiles, temp_dir=None, feedback=None, proxy_opener=None):
            return [os.path.join(temp_dir or str(tmp_path), tile_name + ".tif")]

        monkeypatch.setattr(dd, "download_tiles", _download)

        result = dd.ensure_dem_for_area(0.0, 1.0, 0.0, 1.0)
        assert result is not None
        assert result.endswith(".tif")

    def test_all_downloads_fail_returns_none(self, tmp_path, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))

        monkeypatch.setattr(dd, "required_tiles", lambda *a, **kw: ["N00E000", "N01E000"])

        def _download(*a, **kw):
            return []

        monkeypatch.setattr(dd, "download_tiles", _download)

        result = dd.ensure_dem_for_area(0.0, 2.0, 0.0, 2.0)
        assert result is None


class TestRequiredTilesTooMany:
    def test_too_many_tiles_raises(self, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        monkeypatch.setattr(dd, "_MAX_TILES", 1)

        fake_geom = MagicMock()
        fake_geom.isEmpty.return_value = False
        dd.QgsGeometry.fromRect.return_value = fake_geom
        dd.QgsGeometry.fromPolygonXY.return_value = fake_geom
        fake_geom.intersection.return_value = fake_geom
        monkeypatch.setattr(dd, "longitude_intervals",
            lambda w, e: [(math.floor(w), math.ceil(e))])

        with pytest.raises(ValueError, match="Reduce"):
            dd.required_tiles(0.0, 10.0, 0.0, 10.0, max_tiles=1)


class TestClipAndMerge:
    def test_clip_and_merge_uses_temp_dir(self, monkeypatch):
        dd, tile_base = _import_dem_downloader()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: "/tmp/test")

        captured = {}
        def _fake_clip(*a, **kw):
            captured.update(kw)
            return "/tmp/merged.tif"

        monkeypatch.setattr(dd, "clip_and_merge_tiles", _fake_clip)

        result = dd.clip_and_merge(
            ["tile1.tif", "tile2.tif"],
            south=0.0, north=1.0, west=0.0, east=1.0,
        )
        assert result == "/tmp/merged.tif"


class TestTileNameFor:
    def test_tile_name_mid_lat_lon(self, monkeypatch):
        dd, _ = _import_dem_downloader()
        assert dd.tile_name_for(45, 45) == "Copernicus_DSM_COG_10_N45_00_E045_00_DEM"

    def test_tile_name_south_west(self, monkeypatch):
        dd, _ = _import_dem_downloader()
        result = dd.tile_name_for(-30, -75)
        assert result.startswith("Copernicus_DSM_COG_10_S30_00_W075_00_DEM")

    def test_tile_name_zero_coords(self, monkeypatch):
        dd, _ = _import_dem_downloader()
        result = dd.tile_name_for(0, 0)
        assert "N00_00" in result
        assert "E000_00" in result
