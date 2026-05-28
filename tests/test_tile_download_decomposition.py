# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the four helpers extracted from download_tile_with_retry."""

import urllib.error
import hashlib

import tile_download_base as tdb


class Feedback:
    def __init__(self, canceled=False):
        self.messages = []
        self._canceled = canceled

    def pushInfo(self, message):
        self.messages.append(message)

    def isCanceled(self):
        return self._canceled


class FakeBand:
    def __init__(self, stats):
        self._stats = stats

    def ComputeStatistics(self, _approx_ok):
        return self._stats


class FakeDataset:
    RasterCount = 1
    RasterXSize = 256
    RasterYSize = 256

    def __init__(self, stats=(1.0, 1.0)):
        self._stats = stats

    def GetRasterBand(self, _idx):
        return FakeBand(self._stats)


class FakeResponse:
    def __init__(self, url, chunks, headers=None):
        self._url = url
        self._chunks = list(chunks)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self):
        return self._url

    def read(self, _size):
        if self._chunks:
            return self._chunks.pop(0)
        return b""


class FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, url, timeout):
        return self.response


# --- _classify_http_error tests ---

def test_classify_http_error_404_is_give_up():
    error = urllib.error.HTTPError("http://example.test", 404, "not found", {}, None)
    action, wait = tdb._classify_http_error(error, 0)
    assert action == tdb._GIVE_UP
    assert wait == 0.0


def test_classify_http_error_429_with_retry_after():
    error = urllib.error.HTTPError("http://example.test", 429, "rate limit",
                                   {"Retry-After": "5"}, None)
    action, wait = tdb._classify_http_error(error, 0)
    assert action == tdb._RETRY_AFTER
    assert wait == 5.0


def test_classify_http_error_408_without_retry_after():
    error = urllib.error.HTTPError("http://example.test", 408, "timeout", {}, None)
    action, wait = tdb._classify_http_error(error, 0)
    assert action == tdb._RETRY_BACKOFF
    assert wait > 0


def test_classify_http_error_500_is_retry_backoff():
    error = urllib.error.HTTPError("http://example.test", 503, "unavailable", {}, None)
    action, wait = tdb._classify_http_error(error, 0)
    assert action == tdb._RETRY_BACKOFF
    assert wait > 0


def test_classify_http_error_400_is_give_up():
    error = urllib.error.HTTPError("http://example.test", 400, "bad request", {}, None)
    action, wait = tdb._classify_http_error(error, 0)
    assert action == tdb._GIVE_UP
    assert wait == 0.0


def test_classify_http_error_generic_is_retry_backoff():
    error = OSError("connection refused")
    action, wait = tdb._classify_http_error(error, 0)
    assert action == tdb._RETRY_BACKOFF
    assert wait > 0


# --- _serve_from_cache tests ---

def test_serve_from_cache_returns_none_when_file_missing(tmp_path):
    result = tdb._serve_from_cache(str(tmp_path / "missing.tif"), "missing", None)
    assert result is None


def test_serve_from_cache_returns_path_on_valid_cache(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"cached")
    (tmp_path / "tile.tif.sha256").write_text(hashlib.sha256(b"cached").hexdigest())
    feedback = Feedback()

    monkeypatch.setattr(tdb.gdal, "Open", lambda _p: FakeDataset(stats=(7.0, 7.0)))

    result = tdb._serve_from_cache(str(local_tif), "tile", feedback)
    assert result == str(local_tif)
    assert feedback.messages == ["Cache hit: tile"]


def test_serve_from_cache_unlinks_degenerate_tile(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"bad")

    class DegenerateDataset(FakeDataset):
        RasterXSize = 0

    monkeypatch.setattr(tdb.gdal, "Open", lambda _p: DegenerateDataset())

    result = tdb._serve_from_cache(str(local_tif), "tile", None)
    assert result is None
    assert not local_tif.exists()


# --- _validate_downloaded_tile tests ---

def test_validate_downloaded_tile_returns_true_for_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(tdb.gdal, "Open", lambda _p: FakeDataset())
    assert tdb._validate_downloaded_tile(str(tmp_path / "valid.tif")) is True


def test_validate_downloaded_tile_returns_false_for_corrupt(tmp_path, monkeypatch):
    monkeypatch.setattr(tdb.gdal, "Open", lambda _p: None)
    assert tdb._validate_downloaded_tile(str(tmp_path / "corrupt.tif")) is False


# --- _download_to_tmp tests ---

def test_download_to_tmp_returns_none_on_cancel(tmp_path):
    feedback = Feedback(canceled=True)
    opener = FakeOpener(FakeResponse("http://example.test/tile.tif", [b"data"]))

    bytes_recv, _expected = tdb._download_to_tmp(
        opener, "http://example.test/tile.tif",
        str(tmp_path / "tile.tif.tmp"), None, 60, 250 * 1024 * 1024,
        "tile", feedback)
    assert bytes_recv is None
