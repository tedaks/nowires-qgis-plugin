# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for tile-cache validation tolerance to ComputeStatistics failure.

Cached tiles with valid structural integrity (gdal.Open succeeds, RasterCount >= 1,
non-degenerate dimensions) must be treated as cache hits even when
ComputeStatistics fails. The previous behaviour purged otherwise-valid files on
any stats-read failure, causing unnecessary re-downloads.
"""

import hashlib
import tile_download_base as tdb


class _Feedback:
    def __init__(self):
        self.messages = []

    def pushInfo(self, message):
        self.messages.append(message)

    def isCanceled(self):
        return False


class _NoCallOpener:
    """Opener that fails the test if any HTTP request is attempted."""

    def open(self, url, timeout):  # pragma: no cover - must not be invoked
        raise AssertionError("opener.open() called; cache was incorrectly purged")


def _ds_with_broken_stats():
    class _Band:
        def ComputeStatistics(self, _approx_ok):
            raise RuntimeError("simulated stats failure")

    class _DS:
        RasterCount = 1
        RasterXSize = 256
        RasterYSize = 256

        def GetRasterBand(self, _idx):
            return _Band()

    return _DS()


def _ds_stats_returns_none():
    class _Band:
        def ComputeStatistics(self, _approx_ok):
            return None

    class _DS:
        RasterCount = 1
        RasterXSize = 256
        RasterYSize = 256

        def GetRasterBand(self, _idx):
            return _Band()

    return _DS()


def test_cache_hit_when_compute_statistics_raises(tmp_path, monkeypatch):
    """RuntimeError from ComputeStatistics must not invalidate a structurally-valid cache."""
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"cached content")
    _sidecar = tmp_path / "tile.tif.sha256"
    _sidecar.write_text(hashlib.sha256(b"cached content").hexdigest())

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: _ds_with_broken_stats())

    feedback = _Feedback()
    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        feedback=feedback,
        max_retries=1,
        opener=_NoCallOpener(),
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"cached content"
    assert any("Cache hit" in m for m in feedback.messages)


def test_cache_hit_when_compute_statistics_returns_none(tmp_path, monkeypatch):
    """A None return from ComputeStatistics must not invalidate a structurally-valid cache."""
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"cached content")
    _sidecar = tmp_path / "tile.tif.sha256"
    _sidecar.write_text(hashlib.sha256(b"cached content").hexdigest())

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: _ds_stats_returns_none())

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=_NoCallOpener(),
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"cached content"


def test_cache_purged_when_gdal_open_returns_none(tmp_path, monkeypatch):
    """Structural failure (gdal.Open is None) must still purge and re-download."""
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"corrupt")

    class _GoodDS:
        RasterCount = 1
        RasterXSize = 256
        RasterYSize = 256

        def GetRasterBand(self, _idx):  # pragma: no cover - not reached
            class _Band:
                def ComputeStatistics(self, _approx_ok):
                    return (1.0, 1.0)
            return _Band()

    open_results = iter([None, _GoodDS()])
    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: next(open_results))

    class _Response:
        headers = {"Content-Length": "5"}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def geturl(self):
            return "https://example.test/tile.tif"

        def read(self, _size):
            data = getattr(self, "_sent", False)
            if data:
                return b""
            self._sent = True
            return b"fresh"

    class _Opener:
        def __init__(self):
            self.calls = 0

        def open(self, _url, timeout=None):
            self.calls += 1
            return _Response()

    opener = _Opener()
    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=opener,
    )

    assert result == str(local_tif)
    assert opener.calls == 1
    assert local_tif.read_bytes() == b"fresh"


def test_cache_purged_when_dimensions_degenerate(tmp_path, monkeypatch):
    """Structural failure (zero rows/cols) must still purge and re-download."""
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"degenerate")

    class _Degenerate:
        RasterCount = 1
        RasterXSize = 0
        RasterYSize = 0

        def GetRasterBand(self, _idx):  # pragma: no cover - not reached
            class _Band:
                def ComputeStatistics(self, _approx_ok):
                    return (1.0, 1.0)
            return _Band()

    class _GoodDS:
        RasterCount = 1
        RasterXSize = 256
        RasterYSize = 256

        def GetRasterBand(self, _idx):  # pragma: no cover - not reached
            class _Band:
                def ComputeStatistics(self, _approx_ok):
                    return (1.0, 1.0)
            return _Band()

    open_results = iter([_Degenerate(), _GoodDS()])
    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: next(open_results))

    class _Response:
        headers = {"Content-Length": "5"}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def geturl(self):
            return "https://example.test/tile.tif"

        def read(self, _size):
            if getattr(self, "_sent", False):
                return b""
            self._sent = True
            return b"fresh"

    class _Opener:
        def __init__(self):
            self.calls = 0

        def open(self, _url, timeout=None):
            self.calls += 1
            return _Response()

    opener = _Opener()
    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=opener,
    )

    assert result == str(local_tif)
    assert opener.calls == 1
    assert local_tif.read_bytes() == b"fresh"
