# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for download_tile_with_retry covering missed lines in tile_download_base.py."""

import hashlib
import os
import re
import urllib.error
from unittest.mock import mock_open, patch

import pytest
import tile_download_base as tdb

try:
    import qgis.core  # noqa: F401
    _HAS_REAL_QGIS = True
except ImportError:
    _HAS_REAL_QGIS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_real_gdal():
    try:
        from osgeo import gdal
        from unittest.mock import MagicMock as _MM
        return not isinstance(gdal, _MM)
    except ImportError:
        return False


def _create_valid_tif(path):
    from osgeo import gdal
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, 2, 2, 1, gdal.GDT_Byte)
    band = ds.GetRasterBand(1)
    band.Fill(0)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None


class _Feedback:
    def __init__(self, canceled=False):
        self.messages = []
        self._canceled = canceled

    def pushInfo(self, msg):
        self.messages.append(msg)

    def pushWarning(self, msg):
        self.messages.append(msg)

    def isCanceled(self):
        return self._canceled


class _CounterFeedback:
    """Feedback whose isCanceled returns True after N calls."""

    def __init__(self, cancel_after=3):
        self.messages = []
        self._call_count = 0
        self._cancel_after = cancel_after

    def pushInfo(self, msg):
        self.messages.append(msg)

    def pushWarning(self, msg):
        self.messages.append(msg)

    def isCanceled(self):
        self._call_count += 1
        return self._call_count > self._cancel_after


class _FakeResponse:
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


class _FakeOpener:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def open(self, url, timeout):
        self.calls.append((url, timeout))
        return self.response


class _SequenceOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def open(self, url, timeout):
        self.calls.append((url, timeout))
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


class _FakeBand:
    def __init__(self, stats=(1.0, 1.0)):
        self._stats = stats

    def ComputeStatistics(self, _approx_ok):
        return self._stats


class _FakeDataset:
    RasterCount = 1
    RasterXSize = 256
    RasterYSize = 256

    def GetRasterBand(self, _idx):
        return _FakeBand()


class _DegenerateDataset:
    RasterCount = 1
    RasterXSize = 0
    RasterYSize = 0

    def GetRasterBand(self, _idx):
        return _FakeBand()


# ---------------------------------------------------------------------------
# Test 1: Cancel mid-download — flush (not close), tmp cleanup
# Covers lines: 104-110 (cancel during chunk read, f.flush, os.unlink)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(_HAS_REAL_QGIS, reason="mock_open interferes with QGIS runtime")
def test_cancel_mid_download_flushes_and_cleans_tmp():
    """Cancel during chunk read must call f.flush() and remove tmp.

    Verifies the Issue #7 fix: explicit f.flush() is used instead of
    f.close() to avoid double-close when the context manager exits.
    """
    feedback = _CounterFeedback(cancel_after=2)
    response = _FakeResponse(
        "https://example.test/tile.tif",
        [b"chunk1", b"chunk2"],
    )
    opener = _FakeOpener(response)

    m = mock_open()
    with patch("builtins.open", m):
        result = tdb.download_tile_with_retry(
            tile_url="https://example.test/tile.tif",
            local_tif="/tmp/test_tile.tif",
            base_name_label="test",
            feedback=feedback,
            max_retries=1,
            opener=opener,
        )

    assert result is None
    handle = m.return_value
    handle.flush.assert_called()
    handle.close.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Valid tile name rejected by regex
# Covers lines: 46-48
# ---------------------------------------------------------------------------

def test_valid_tile_name_rejected():
    """base_name_label not matching valid_tile_re returns None without download."""
    opener = _FakeOpener(_FakeResponse("https://example.test/bad.tif", [b"bad"]))
    feedback = _Feedback()

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/bad.tif",
        local_tif="/tmp/bad.tif",
        base_name_label="../bad",
        valid_tile_re=re.compile(r"^[A-Z0-9_]+$"),
        feedback=feedback,
        opener=opener,
    )

    assert result is None
    assert opener.calls == []


# ---------------------------------------------------------------------------
# Test 3: Cache hit — valid TIFF reused, no download
# Covers lines: 50, 54-61 (cache validation and early return)
# ---------------------------------------------------------------------------

@pytest.mark.gdal_integration
@pytest.mark.skipif(not _has_real_gdal(), reason="Real GDAL not available")
def test_cache_hit_reuses_valid_tif(tmp_path):
    """Valid cached TIFF is reused without re-downloading."""
    local_tif = tmp_path / "tile.tif"
    _create_valid_tif(str(local_tif))
    (tmp_path / "tile.tif.sha256").write_text(
        hashlib.sha256(local_tif.read_bytes()).hexdigest())
    feedback = _Feedback()
    opener = _FakeOpener(
        _FakeResponse("https://example.test/tile.tif", [b"new"])
    )

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        feedback=feedback,
        opener=opener,
    )

    assert result == str(local_tif)
    assert opener.calls == []
    assert "Cache hit: tile" in feedback.messages


# ---------------------------------------------------------------------------
# Test 4: Degenerate cached tile — zero dimensions, re-downloaded
# Covers lines: 62-64, 66, 69-72, 73-74, 101, 113, 139-140
# ---------------------------------------------------------------------------

@pytest.mark.gdal_integration
@pytest.mark.skipif(not _has_real_gdal(), reason="Real GDAL not available")
def test_degenerate_cached_tile_replaced(tmp_path, monkeypatch):
    """Cached TIFF with zero raster dimensions is deleted and re-downloaded."""
    from osgeo import gdal

    local_tif = tmp_path / "tile.tif"
    _create_valid_tif(str(local_tif))
    feedback = _Feedback()
    opener = _FakeOpener(
        _FakeResponse(
            "https://example.test/tile.tif",
            [b"newdata"],
        )
    )

    open_results = iter([_DegenerateDataset(), _FakeDataset()])

    def _mock_open(path):
        return next(open_results)

    monkeypatch.setattr(gdal, "Open", _mock_open)
    monkeypatch.setattr(tdb.gdal, "Open", _mock_open)

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        feedback=feedback,
        max_retries=2,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"newdata"
    assert len(opener.calls) == 1
    assert any("Downloading" in msg for msg in feedback.messages)


# ---------------------------------------------------------------------------
# Test 5: Corrupt cached tile — gdal.Open returns None, re-downloaded
# Covers lines: 67-68, 69-72, 73-74, 101, 113, 139-140
# ---------------------------------------------------------------------------

@pytest.mark.gdal_integration
@pytest.mark.skipif(not _has_real_gdal(), reason="Real GDAL not available")
def test_corrupt_cached_tile_replaced(tmp_path, monkeypatch):
    """Corrupt cached file (gdal.Open returns None) is deleted and re-downloaded."""
    from osgeo import gdal

    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"not a valid tiff file")
    feedback = _Feedback()
    opener = _FakeOpener(
        _FakeResponse(
            "https://example.test/tile.tif",
            [b"newdata"],
        )
    )

    open_results = iter([None, _FakeDataset()])

    def _mock_open(path):
        return next(open_results)

    monkeypatch.setattr(gdal, "Open", _mock_open)
    monkeypatch.setattr(tdb.gdal, "Open", _mock_open)

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        feedback=feedback,
        max_retries=2,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"newdata"
    assert len(opener.calls) == 1
    assert any("Downloading" in msg for msg in feedback.messages)


# ---------------------------------------------------------------------------
# Test 6: Wall clock budget exceeded
# Covers lines: 82-87
# ---------------------------------------------------------------------------

def test_wall_clock_budget_exceeded_stops_before_opening(tmp_path):
    """Zero wall_clock_budget stops download before any opener call."""
    feedback = _Feedback()
    opener = _FakeOpener(
        _FakeResponse("https://example.test/tile.tif", [b"new"])
    )

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(tmp_path / "tile.tif"),
        base_name_label="tile",
        feedback=feedback,
        opener=opener,
        wall_clock_budget=0,
    )

    assert result is None
    assert opener.calls == []
    assert "Download budget exceeded: tile" in feedback.messages


# ---------------------------------------------------------------------------
# Test 7: HTTP 404 returns None without retry
# Covers lines: 157-161
# ---------------------------------------------------------------------------

def test_http_404_returns_none(tmp_path):
    """HTTP 404 is not retried and returns None."""
    feedback = _Feedback()
    error = urllib.error.HTTPError(
        "https://example.test/missing.tif", 404, "not found", hdrs={}, fp=None,
    )
    opener = _SequenceOpener([error])

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/missing.tif",
        local_tif=str(tmp_path / "missing.tif"),
        base_name_label="missing",
        feedback=feedback,
        max_retries=3,
        opener=opener,
    )

    assert result is None
    assert len(opener.calls) == 1
    assert "Tile not available (HTTP 404): missing" in feedback.messages


# ---------------------------------------------------------------------------
# Test 8: HTTP 500 retries twice then succeeds
# Covers lines: 162-163, 170, 173, 177, 101, 113, 139-140
# ---------------------------------------------------------------------------

def test_http_500_retries_then_succeeds(tmp_path, monkeypatch):
    """HTTP 500 uses exponential backoff (no Retry-After) and succeeds after retries."""
    local_tif = tmp_path / "tile.tif"
    sleeps = []
    feedback = _Feedback()
    error = urllib.error.HTTPError(
        "https://example.test/tile.tif", 500, "server error", hdrs={}, fp=None,
    )
    opener = _SequenceOpener([
        error,
        error,
        _FakeResponse(
            "https://example.test/tile.tif",
            [b"ok"],
        ),
    ])

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: _FakeDataset())
    monkeypatch.setattr(tdb.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        feedback=feedback,
        max_retries=3,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"ok"
    assert len(opener.calls) == 3
    assert len(sleeps) == 2
    assert sleeps[0] >= 1.0
    assert sleeps[1] >= 2.0


# ---------------------------------------------------------------------------
# Test 9: HTTP non-retryable codes (403) return None
# Covers lines: 178-184
# ---------------------------------------------------------------------------

def test_http_403_returns_none_without_retry(tmp_path):
    """HTTP 403 (non-retryable) returns None without retrying."""
    feedback = _Feedback()
    error = urllib.error.HTTPError(
        "https://example.test/forbidden.tif", 403, "forbidden", hdrs={}, fp=None,
    )
    opener = _SequenceOpener([error])

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/forbidden.tif",
        local_tif=str(tmp_path / "forbidden.tif"),
        base_name_label="forbidden",
        feedback=feedback,
        max_retries=3,
        opener=opener,
    )

    assert result is None
    assert len(opener.calls) == 1
    assert any("non-retryable" in msg.lower() for msg in feedback.messages)


# ---------------------------------------------------------------------------
# Test 10: Redirect to different host raises RuntimeError
# Covers lines: 91-94
# ---------------------------------------------------------------------------

def test_redirect_to_different_host_raises_runtime_error(tmp_path):
    """Redirect to a different host raises RuntimeError and returns None."""
    local_tif = tmp_path / "tile.tif"
    feedback = _Feedback()
    opener = _FakeOpener(
        _FakeResponse(
            "https://evil.example/tile.tif",
            [b"malicious"],
        )
    )

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        base_url="https://example.test/",
        feedback=feedback,
        max_retries=1,
        opener=opener,
    )

    assert result is None
    assert not local_tif.exists()
    tmp_path_file = str(local_tif) + ".tmp"
    assert not os.path.exists(tmp_path_file)
    assert any("redirect" in msg.lower() for msg in feedback.messages)
