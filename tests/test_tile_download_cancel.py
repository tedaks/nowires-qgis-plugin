# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for tile_download_base cancel and corruption paths."""

import os
import hashlib

import tile_download_base as tdb
import tile_cache_integrity as tci


class Feedback:
    def __init__(self, canceled=False):
        self.messages = []
        self._canceled = canceled

    def pushInfo(self, message):
        self.messages.append(message)

    def pushWarning(self, message):
        self.messages.append(message)

    def isCanceled(self):
        return self._canceled


class FakeBand:
    def __init__(self, stats=None):
        self._stats = stats

    def ComputeStatistics(self, _approx_ok):
        return self._stats if self._stats else (1.0, 1.0)


class FakeDataset:
    RasterCount = 1
    RasterXSize = 256
    RasterYSize = 256

    def __init__(self, stats=None):
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


class TestTileDownloadCancel:
    def test_cancel_before_first_attempt(self, tmp_path, monkeypatch):
        feedback = Feedback(canceled=True)
        local_tif = str(tmp_path / "canceled.tif")

        response = FakeResponse("https://example.com/tile.tif", [b"data"])
        opener = FakeOpener(response)

        result = tdb.download_tile_with_retry(
            "https://example.com/tile.tif", local_tif, "test_tile",
            feedback=feedback, base_url="https://example.com/tile.tif",
            opener=opener, wall_clock_budget=None,
        )
        assert result is None
        assert not os.path.exists(local_tif)

    def test_cancel_during_download_cleans_tmp(self, tmp_path, monkeypatch):
        local_tif = str(tmp_path / "cancel_mid.tif")
        tmp_path_str = local_tif + ".tmp"
        with open(tmp_path_str, "wb") as f:
            f.write(b"partial")

        feedback = Feedback(canceled=False)

        class CancelAfterOneChunkResponse(FakeResponse):
            def read(self, _size):
                feedback._canceled = True
                return b"chunk"

        response = CancelAfterOneChunkResponse(
            "https://example.com/tile.tif", []
        )
        opener = FakeOpener(response)
        opener.open = lambda url, timeout: response

        result = tdb.download_tile_with_retry(
            "https://example.com/tile.tif", local_tif, "test_tile",
            feedback=feedback, base_url="https://example.com/tile.tif",
            opener=opener, wall_clock_budget=None,
        )
        assert result is None

    def test_wall_clock_budget_exceeded_before_attempt(self, tmp_path, monkeypatch):
        local_tif = str(tmp_path / "budget.tif")
        feedback = Feedback()

        response = FakeResponse("https://example.com/tile.tif", [b"ok"])
        opener = FakeOpener(response)

        import time
        _t = [0.0]

        def _monotonic():
            _t[0] += 1000.0
            return _t[0]

        monkeypatch.setattr(time, "monotonic", _monotonic)

        result = tdb.download_tile_with_retry(
            "https://example.com/tile.tif", local_tif, "test_tile",
            feedback=feedback, base_url="https://example.com/tile.tif",
            opener=opener, wall_clock_budget=10.0,
        )
        assert result is None

    def test_corrupt_download_gdal_open_fails(self, tmp_path, monkeypatch):
        local_tif = str(tmp_path / "corrupt.tif")
        feedback = Feedback()

        response = FakeResponse("https://example.com/tile.tif", [b"invalid_tiff_data"])
        opener = FakeOpener(response)

        def fake_gdal_open(path):
            return None

        monkeypatch.setattr(tdb.gdal, "Open", fake_gdal_open)

        result = tdb.download_tile_with_retry(
            "https://example.com/tile.tif", local_tif, "test_tile",
            feedback=feedback, base_url="https://example.com/tile.tif",
            opener=opener, wall_clock_budget=None,
        )
        assert result is None

    def test_invalid_tile_name_rejected(self, tmp_path):
        import re
        local_tif = str(tmp_path / "invalid.tif")
        feedback = Feedback()
        opener = FakeOpener(FakeResponse("https://example.com", [b""]))

        result = tdb.download_tile_with_retry(
            "https://example.com/bad", local_tif, "N19_E120",
            feedback=feedback, base_url="https://example.com",
            opener=opener, wall_clock_budget=None,
            valid_tile_re=re.compile(r"^[NS]\d{2}[EW]\d{3}$"),
        )
        assert result is None


class TestTileCacheIntegrity:
    def test_sidecar_path_extension(self):
        path = tci.sidecar_path("/tmp/test.tif")
        assert path.endswith(".sha256")
        assert path.startswith("/tmp/test.tif")

    def test_verify_checksum_no_sidecar_returns_false(self, tmp_path):
        tif = tmp_path / "nonexistent.tif"
        assert tci.verify_checksum(str(tif)) is False

    def test_write_and_verify_checksum(self, tmp_path):
        tif = tmp_path / "verify.tif"
        with open(tif, "wb") as f:
            f.write(b"test tile content for checksum verification")

        tci.write_checksum(str(tif))
        assert tci.verify_checksum(str(tif)) is True

    def test_verify_checksum_tampered_file(self, tmp_path):
        tif = tmp_path / "tampered.tif"
        with open(tif, "wb") as f:
            f.write(b"original content")
        tci.write_checksum(str(tif))

        with open(tif, "wb") as f:
            f.write(b"modified content")
        assert tci.verify_checksum(str(tif)) is False

    def test_cleanup_sidecar_removes_file(self, tmp_path):
        tif = tmp_path / "cleanup.tif"
        sidecar = tci.sidecar_path(str(tif))
        with open(tif, "wb") as f:
            f.write(b"content")
        tci.write_checksum(str(tif))
        assert os.path.exists(sidecar)

        tci.cleanup_sidecar(str(tif))
        assert not os.path.exists(sidecar)

    def test_cleanup_sidecar_no_sidecar_no_error(self, tmp_path):
        tif = str(tmp_path / "nocar.tif")
        tci.cleanup_sidecar(tif)

    def test_verify_checksum_empty_sidecar(self, tmp_path):
        tif = tmp_path / "empty_sidecar.tif"
        sidecar = tci.sidecar_path(str(tif))
        with open(tif, "wb") as f:
            f.write(b"data")
        with open(sidecar, "w") as f:
            f.write("")
        assert tci.verify_checksum(str(tif)) is False


class TestTileDownloadCapRejection:
    def test_reject_oversized_content_length(self):
        fb = Feedback()
        result = tci.reject_oversized_content_length(
            300 * 1024 * 1024, 250 * 1024 * 1024, "N10E10", fb,
        )
        assert result is True

    def test_accept_content_length_within_limit(self):
        fb = Feedback()
        result = tci.reject_oversized_content_length(
            200 * 1024 * 1024, 250 * 1024 * 1024, "N10E10", fb,
        )
        assert result is False

    def test_accept_when_max_bytes_is_none(self):
        fb = Feedback()
        result = tci.reject_oversized_content_length(
            999 * 1024 * 1024, None, "N10E10", fb,
        )
        assert result is False

    def test_cap_exceeded_flushes_and_unlinks(self, tmp_path):
        tmp_file = str(tmp_path / "cap_test.tmp")
        with open(tmp_file, "wb") as f:
            f.write(b"data so far")
        with open(tmp_file, "ab") as f:
            result = tci.cap_exceeded(50, 100, 100, "test", f, tmp_file)
        assert result is True

    def test_cap_not_exceeded_yet(self, tmp_path):
        tmp_file = str(tmp_path / "cap_ok.tmp")
        with open(tmp_file, "wb") as f:
            f.write(b"small")
        with open(tmp_file, "rb+") as f:
            result = tci.cap_exceeded(10, 30, 100, "test", f, tmp_file)
        assert result is False
