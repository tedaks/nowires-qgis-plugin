# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Unit tests for shared tile download/cache behavior."""

import re
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
        self.calls = []

    def open(self, url, timeout):
        self.calls.append((url, timeout))
        return self.response


class SequenceOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def open(self, url, timeout):
        self.calls.append((url, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_valid_cached_tile_with_constant_stats_is_reused(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"cached")
    (tmp_path / "tile.tif.sha256").write_text(hashlib.sha256(b"cached").hexdigest())
    feedback = Feedback()
    opener = FakeOpener(FakeResponse("https://example.test/tile.tif", [b"new"]))

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: FakeDataset(stats=(7.0, 7.0)))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        feedback=feedback,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"cached"
    assert opener.calls == []
    assert feedback.messages == ["Cache hit: tile"]


def test_degenerate_cached_tile_is_replaced(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"cached")
    opener = FakeOpener(
        FakeResponse(
            "https://example.test/tile.tif",
            [b"fresh"],
            headers={"Content-Length": "5"},
        )
    )

    class DegenerateDataset(FakeDataset):
        RasterXSize = 0

    open_results = iter([DegenerateDataset(), FakeDataset()])
    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: next(open_results))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"fresh"
    assert opener.calls == [("https://example.test/tile.tif", 60)]


def test_download_returns_none_when_feedback_is_canceled(tmp_path):
    opener = FakeOpener(FakeResponse("https://example.test/tile.tif", [b"new"]))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(tmp_path / "tile.tif"),
        base_name_label="tile",
        feedback=Feedback(canceled=True),
        opener=opener,
    )

    assert result is None
    assert opener.calls == []


def test_download_wall_clock_budget_stops_before_opening(tmp_path):
    feedback = Feedback()
    opener = FakeOpener(FakeResponse("https://example.test/tile.tif", [b"new"]))

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
    assert feedback.messages == [
        "Downloading: https://example.test/tile.tif",
        "Download budget exceeded: tile",
    ]


def test_download_succeeds_without_content_length_header(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    opener = FakeOpener(FakeResponse("https://example.test/tile.tif", [b"ok"]))

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: FakeDataset())

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"ok"


def test_incomplete_download_is_rejected_and_tmp_removed(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    opener = FakeOpener(
        FakeResponse(
            "https://example.test/tile.tif",
            [b"bad"],
            headers={"Content-Length": "4"},
        )
    )

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: FakeDataset())

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=opener,
    )

    assert result is None
    assert not local_tif.exists()
    assert not (tmp_path / "tile.tif.tmp").exists()


def test_corrupt_download_retries_and_then_succeeds(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    opener = SequenceOpener(
        [
            FakeResponse(
                "https://example.test/tile.tif",
                [b"bad"],
                headers={"Content-Length": "3"},
            ),
            FakeResponse(
                "https://example.test/tile.tif",
                [b"good"],
                headers={"Content-Length": "4"},
            ),
        ]
    )
    open_results = iter([None, FakeDataset()])

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: next(open_results))
    monkeypatch.setattr(tdb.time, "sleep", lambda _seconds: None)

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=2,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"good"
    assert len(opener.calls) == 2


def test_cross_host_redirect_is_rejected_and_tmp_removed(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    opener = FakeOpener(
        FakeResponse(
            "https://evil.example/tile.tif",
            [b"bad"],
            headers={"Content-Length": "3"},
        )
    )

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: FakeDataset())

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        base_url="https://example.test/",
        opener=opener,
    )

    assert result is None
    assert not local_tif.exists()
    assert not (tmp_path / "tile.tif.tmp").exists()


def test_http_404_is_not_retried(tmp_path):
    feedback = Feedback()
    error = urllib.error.HTTPError(
        "https://example.test/missing.tif",
        404,
        "not found",
        hdrs={},
        fp=None,
    )
    opener = SequenceOpener([error])

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


def test_retryable_http_error_uses_retry_after_then_succeeds(tmp_path, monkeypatch):
    local_tif = tmp_path / "tile.tif"
    sleeps = []
    error = urllib.error.HTTPError(
        "https://example.test/tile.tif",
        429,
        "too many requests",
        hdrs={"Retry-After": "3"},
        fp=None,
    )
    opener = SequenceOpener(
        [
            error,
            FakeResponse(
                "https://example.test/tile.tif",
                [b"ok"],
                headers={"Content-Length": "2"},
            ),
        ]
    )

    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: FakeDataset())
    monkeypatch.setattr(tdb.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=2,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"ok"
    assert sleeps == [3]


def test_invalid_tile_name_is_rejected_before_download(tmp_path):
    opener = FakeOpener(FakeResponse("https://example.test/bad.tif", [b"bad"]))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/bad.tif",
        local_tif=str(tmp_path / "bad.tif"),
        base_name_label="../bad",
        valid_tile_re=re.compile(r"^[A-Z0-9_]+$"),
        opener=opener,
    )

    assert result is None
    assert opener.calls == []
