# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for dem_downloader.py — get_temp_dir edge cases, required_tiles, and feedback paths."""

import importlib
import math
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

_posix_symlink = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlink creation requires elevated privileges on Windows",
)

try:
    import qgis.core  # noqa: F401
    _HAS_REAL_QGIS = True
except ImportError:
    _HAS_REAL_QGIS = False

_skip_if_real_qgis = pytest.mark.skipif(
    _HAS_REAL_QGIS, reason="Test mocks QGIS classes; skip when real QGIS is available"
)


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


# ---------------------------------------------------------------------------
# get_temp_dir edge cases (lines 78‑79, 80‑82, 102‑103, 113‑114)
# ---------------------------------------------------------------------------
class TestGetTempDirEdgeCases:
    @_posix_symlink
    def test_removes_symlink(self, tmp_path, monkeypatch):
        """Lines 78‑79: symlink at target is unlinked before directory creation."""
        dd, _ = _import_dem_downloader()
        monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
        monkeypatch.setattr(dd.getpass, "getuser", lambda: "alice")

        target = tmp_path / "NoWires-alice"
        symlink_dst = tmp_path / "actual-dir"
        symlink_dst.mkdir()
        target.symlink_to(symlink_dst, target_is_directory=True)

        result = dd.get_temp_dir(create=True)
        assert result == str(target)
        assert not target.is_symlink()
        assert target.is_dir()

    def test_removes_non_directory(self, tmp_path, monkeypatch):
        """Lines 80‑82: a plain file at target is unlinked before directory creation."""
        dd, _ = _import_dem_downloader()
        monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
        monkeypatch.setattr(dd.getpass, "getuser", lambda: "alice")

        target = tmp_path / "NoWires-alice"
        target.write_text("stale file content", encoding="utf-8")

        result = dd.get_temp_dir(create=True)
        assert result == str(target)
        assert target.is_dir()
        assert not target.is_file()

    def test_chmod_failure_suppressed(self, tmp_path, monkeypatch):
        """Lines 102‑103: OSError from os.chmod in the mkdtemp fallback is caught."""
        dd, _ = _import_dem_downloader()
        monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
        monkeypatch.setattr(dd.getpass, "getuser", lambda: "alice")

        def _fail_makedirs(*_a, **_kw):
            raise OSError("makedirs refused")

        monkeypatch.setattr(dd.os, "makedirs", _fail_makedirs)
        monkeypatch.setattr(dd.os, "chmod", lambda _p, _m: (_ for _ in ()).throw(
            OSError("chmod refused")))

        result = dd.get_temp_dir(create=True)
        assert result.startswith(str(tmp_path / "NoWires-"))
        assert os.path.isdir(result)

    def test_stat_failure_suppressed(self, tmp_path, monkeypatch):
        """Lines 113‑114: OSError from os.stat after makedirs is caught."""
        dd, _ = _import_dem_downloader()
        monkeypatch.setattr(dd.tempfile, "gettempdir", lambda: str(tmp_path))
        monkeypatch.setattr(dd.getpass, "getuser", lambda: "alice")

        def _stat_raises(_p):
            raise OSError("stat refused")

        monkeypatch.setattr(dd.os, "stat", _stat_raises)

        target = tmp_path / "NoWires-alice"
        result = dd.get_temp_dir(create=True)
        assert result == str(target)


# ---------------------------------------------------------------------------
# tile_name_for edge cases (math.floor behaviour)
# ---------------------------------------------------------------------------
class TestTileNameForFloatBoundary:
    def test_float_input(self, monkeypatch):
        """tile_name_for(14.7, 121.3) applies math.floor: N14_00_E121_00."""
        dd, _ = _import_dem_downloader()
        result = dd.tile_name_for(14.7, 121.3)
        assert result == "Copernicus_DSM_COG_10_N14_00_E121_00_DEM"

    def test_negative_coords(self, monkeypatch):
        """tile_name_for(-33.9, -70.6) floors toward negative: S34_00_W071_00."""
        dd, _ = _import_dem_downloader()
        result = dd.tile_name_for(-33.9, -70.6)
        assert result == "Copernicus_DSM_COG_10_S34_00_W071_00_DEM"


# ---------------------------------------------------------------------------
# required_tiles (lines ‑142‑continue, ‑147‑feedback, ‑157‑return)
# ---------------------------------------------------------------------------
@_skip_if_real_qgis
class TestRequiredTiles:
    def test_single_tile_area(self, monkeypatch):
        """Lines 147, 157: a small area returns one tile with feedback pushInfo."""
        dd, _ = _import_dem_downloader()

        aoi_geom = MagicMock()
        tile_poly = MagicMock()
        intersection = MagicMock()
        intersection.isEmpty.return_value = False
        tile_poly.intersection.return_value = intersection

        dd.QgsGeometry.fromRect.return_value = aoi_geom
        dd.QgsGeometry.fromPolygonXY.return_value = tile_poly
        monkeypatch.setattr(dd, "longitude_intervals", lambda w, e: [(w, e)])

        fb = _Feedback()
        result = dd.required_tiles(0.0, 0.5, 0.0, 0.5, feedback=fb)
        assert len(result) == 1
        assert result[0] == "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"
        assert len(fb.messages) == 1
        assert "Required tile:" in fb.messages[0]

    def test_skips_empty_intersection(self, monkeypatch):
        """Line 142: empty intersection causes continue — no tiles collected."""
        dd, _ = _import_dem_downloader()

        aoi_geom = MagicMock()
        tile_poly = MagicMock()
        intersection = MagicMock()
        intersection.isEmpty.return_value = True
        tile_poly.intersection.return_value = intersection

        dd.QgsGeometry.fromRect.return_value = aoi_geom
        dd.QgsGeometry.fromPolygonXY.return_value = tile_poly
        monkeypatch.setattr(dd, "longitude_intervals", lambda w, e: [(w, e)])

        result = dd.required_tiles(0.0, 10.0, 0.0, 10.0)
        assert result == []


# ---------------------------------------------------------------------------
# download_tiles (line ‑163‑defaut‑temp‑dir)
# ---------------------------------------------------------------------------
class TestDownloadTilesDefaults:
    def test_uses_get_temp_dir_when_temp_dir_is_none(self, tmp_path, monkeypatch):
        """Line 163: when temp_dir is not provided, get_temp_dir() is called."""
        dd, _ = _import_dem_downloader()
        get_temp_dir_calls = []

        def _fake_get_temp_dir():
            get_temp_dir_calls.append(1)
            return str(tmp_path)

        monkeypatch.setattr(dd, "get_temp_dir", _fake_get_temp_dir)
        monkeypatch.setattr(
            dd, "download_tile_with_retry",
            lambda **kw: str(tmp_path / "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif"),
        )

        result = dd.download_tiles(["N00E000"])
        assert len(get_temp_dir_calls) >= 1
        assert len(result) == 1


# ---------------------------------------------------------------------------
# ensure_dem_for_area feedback messages
#    covers lines 209, 214, 218, 226, 232‑245
# ---------------------------------------------------------------------------
class TestEnsureDEMFeedbackMessages:
    def test_no_tiles_feedback(self, tmp_path, monkeypatch):
        """Lines 209, 214: feedback receives calculating + no‑tiles messages."""
        dd, _ = _import_dem_downloader()
        fb = _Feedback()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))
        monkeypatch.setattr(dd, "required_tiles", lambda *a, **kw: [])

        result = dd.ensure_dem_for_area(0.0, 1.0, 0.0, 1.0, feedback=fb)
        assert result is None
        assert "Calculating required GLO-30 tiles" in fb.messages
        assert "No tiles found for the given area." in fb.messages

    def test_download_fail_feedback(self, tmp_path, monkeypatch):
        """Lines 209, 218, 226: feedback reports download attempt and failure."""
        dd, _ = _import_dem_downloader()
        fb = _Feedback()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))
        monkeypatch.setattr(dd, "required_tiles", lambda *a, **kw: ["N00E000"])
        monkeypatch.setattr(dd, "download_tiles", lambda *a, **kw: [])

        result = dd.ensure_dem_for_area(0.0, 1.0, 0.0, 1.0, feedback=fb)
        assert result is None
        assert "Calculating required GLO-30 tiles" in fb.messages
        assert "Downloading DEM tiles" in fb.messages
        assert "No tiles were downloaded successfully." in fb.messages

    def test_single_tile_feedback(self, tmp_path, monkeypatch):
        """Lines 209, 218: single-tile path skips merge messages."""
        dd, _ = _import_dem_downloader()
        fb = _Feedback()
        tile_path = str(tmp_path / "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif")
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))
        monkeypatch.setattr(dd, "required_tiles", lambda *a, **kw: ["N00E000"])
        monkeypatch.setattr(dd, "download_tiles", lambda *a, **kw: [tile_path])

        result = dd.ensure_dem_for_area(0.0, 1.0, 0.0, 1.0, feedback=fb)
        assert result == tile_path
        assert "Calculating required GLO-30 tiles" in fb.messages
        assert "Downloading DEM tiles" in fb.messages
        assert not any("No tiles were downloaded" in m for m in fb.messages)
        assert not any("Clipping" in m for m in fb.messages)

    def test_clip_merge_feedback(self, tmp_path, monkeypatch):
        """Lines 209, 218, 232‑245: multi‑tile path reports merge and per‑run folder."""
        dd, _ = _import_dem_downloader()
        fb = _Feedback()
        monkeypatch.setattr(dd, "get_temp_dir", lambda: str(tmp_path))
        monkeypatch.setattr(
            dd, "required_tiles",
            lambda *a, **kw: ["Copernicus_DSM_COG_10_N00_00_E000_00_DEM",
                               "Copernicus_DSM_COG_10_N01_00_E000_00_DEM"],
        )
        monkeypatch.setattr(
            dd, "download_tiles",
            lambda *a, **kw: [
                str(tmp_path / "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif"),
                str(tmp_path / "Copernicus_DSM_COG_10_N01_00_E000_00_DEM.tif"),
            ],
        )
        monkeypatch.setattr(dd, "clip_and_merge",
            lambda *a, **kw: str(tmp_path / "merged_dem.tif"))

        result = dd.ensure_dem_for_area(0.0, 2.0, 0.0, 1.0, feedback=fb)
        assert result is not None
        assert "Calculating required GLO-30 tiles" in fb.messages
        assert "Downloading DEM tiles" in fb.messages
        assert "Clipping and merging DEM tiles" in fb.messages
        assert any("Merged DEM outputs" in m for m in fb.messages)


# ---------------------------------------------------------------------------
# Existing tests (kept unchanged)
# ---------------------------------------------------------------------------
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


@_skip_if_real_qgis
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
