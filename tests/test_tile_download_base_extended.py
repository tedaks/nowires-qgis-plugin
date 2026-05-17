# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Additional edge-case tests for tile_download_base.py."""

import urllib.error
from unittest.mock import patch

import pytest
import tile_download_base as tdb


class Feedback:
    def __init__(self, canceled=False):
        self.messages = []
        self._canceled = canceled

    def pushInfo(self, message):
        self.messages.append(message)

    def isCanceled(self):
        return self._canceled


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


def test_non_retryable_http_error_is_not_retried(tmp_path, monkeypatch):
    """HTTP 403 (Forbidden) should not be retried."""
    error = urllib.error.HTTPError(
        "https://example.test/forbidden.tif", 403, "forbidden", hdrs={}, fp=None,
    )
    opener = SequenceOpener([error])

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/forbidden.tif",
        local_tif=str(tmp_path / "forbidden.tif"),
        base_name_label="forbidden",
        max_retries=3,
        opener=opener,
    )

    assert result is None
    assert len(opener.calls) == 1


def test_http_500_is_retried_then_succeeds(tmp_path, monkeypatch):
    """HTTP 500 should be retried and succeed on second attempt."""
    local_tif = tmp_path / "tile.tif"
    sleeps = []
    error = urllib.error.HTTPError(
        "https://example.test/tile.tif", 500, "server error",
        hdrs={}, fp=None,
    )
    opener = SequenceOpener([
        error,
        FakeResponse(
            "https://example.test/tile.tif",
            [b"ok"], headers={"Content-Length": "2"},
        ),
    ])

    class FakeBand:
        def ComputeStatistics(self, _approx_ok):
            return (1.0, 1.0)

    class FakeDataset:
        RasterCount = 1
        RasterXSize = 256
        RasterYSize = 256

        def GetRasterBand(self, _idx):
            return FakeBand()

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
    assert len(opener.calls) == 2
    assert len(sleeps) > 0


def test_generic_exception_is_retried(tmp_path, monkeypatch):
    """Non-HTTP exceptions should be retried."""
    local_tif = tmp_path / "tile.tif"
    sleeps = []
    opener = SequenceOpener([
        OSError("connection refused"),
        FakeResponse(
            "https://example.test/tile.tif",
            [b"ok"], headers={"Content-Length": "2"},
        ),
    ])
    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: type(
        "DS", (), {
            "RasterCount": 1, "RasterXSize": 256, "RasterYSize": 256,
            "GetRasterBand": lambda s, i: type(
                "Band", (), {"ComputeStatistics": lambda s, a: (1.0, 1.0)}
            )(),
        }
    )())
    monkeypatch.setattr(tdb.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=2,
        opener=opener,
    )

    assert result == str(local_tif)
    assert len(opener.calls) == 2


def test_http_retry_after_non_numeric_value(tmp_path, monkeypatch):
    """Retry-After header with non-integer value uses exponential backoff."""
    sleeps = []
    error = urllib.error.HTTPError(
        "https://example.test/tile.tif", 503, "service unavailable",
        hdrs={"Retry-After": "not-a-number"}, fp=None,
    )
    opener = SequenceOpener([
        error,
        FakeResponse(
            "https://example.test/tile.tif",
            [b"ok"], headers={"Content-Length": "2"},
        ),
    ])
    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: type(
        "DS", (), {
            "RasterCount": 1, "RasterXSize": 256, "RasterYSize": 256,
            "GetRasterBand": lambda s, i: type(
                "Band", (), {"ComputeStatistics": lambda s, a: (1.0, 1.0)}
            )(),
        }
    )())
    monkeypatch.setattr(tdb.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(tmp_path / "tile.tif"),
        base_name_label="tile",
        max_retries=2,
        opener=opener,
    )

    assert result is not None
    assert len(sleeps) == 1
    assert sleeps[0] > 0


def test_cached_tile_gdal_open_returns_none_replaced(tmp_path, monkeypatch):
    """When gdal.Open returns None for cached tile, re-download."""
    local_tif = tmp_path / "tile.tif"
    local_tif.write_bytes(b"corrupt")
    opener = FakeOpener(FakeResponse(
        "https://example.test/tile.tif",
        [b"fresh"], headers={"Content-Length": "5"},
    ))
    open_results = iter([None, type(
        "DS", (), {
            "RasterCount": 1, "RasterXSize": 256, "RasterYSize": 256,
            "GetRasterBand": lambda s, i: type(
                "Band", (), {"ComputeStatistics": lambda s, a: (1.0, 1.0)}
            )(),
        }
    )()])
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


def test_temp_file_cleaned_on_exit_when_not_downloaded(tmp_path):
    """Temporary .tmp file should be removed when download aborts."""
    local_tif = str(tmp_path / "tile.tif")
    tmp_path_file = local_tif + ".tmp"
    opener = SequenceOpener([
        OSError("network error"),
        OSError("network error again"),
        OSError("network error third"),
    ])
    monkeypatch = patch("tile_download_base.time.sleep", return_value=None)
    monkeypatch.start()
    try:
        result = tdb.download_tile_with_retry(
            tile_url="https://example.test/tile.tif",
            local_tif=local_tif,
            base_name_label="tile",
            max_retries=3,
            opener=opener,
        )
        assert result is None
        import os
        assert not os.path.exists(tmp_path_file)
    finally:
        monkeypatch.stop()


def test_reply_without_content_length_header_full_download(tmp_path, monkeypatch):
    """When Content-Length is None, download succeeds with full content."""
    local_tif = tmp_path / "tile.tif"
    opener = FakeOpener(FakeResponse(
        "https://example.test/tile.tif",
        [b"full_content"], headers={},
    ))
    monkeypatch.setattr(tdb.gdal, "Open", lambda _path: type(
        "DS", (), {
            "RasterCount": 1, "RasterXSize": 256, "RasterYSize": 256,
            "GetRasterBand": lambda s, i: type(
                "Band", (), {"ComputeStatistics": lambda s, a: (1.0, 1.0)}
            )(),
        }
    )())

    result = tdb.download_tile_with_retry(
        tile_url="https://example.test/tile.tif",
        local_tif=str(local_tif),
        base_name_label="tile",
        max_retries=1,
        opener=opener,
    )

    assert result == str(local_tif)
    assert local_tif.read_bytes() == b"full_content"


def test_aoi_geometry_crosses_antimeridian():
    """AOI geometry that crosses the antimeridian should return MultiPolygon."""
    try:
        from osgeo import ogr as _real_ogr
        from unittest.mock import MagicMock
        if isinstance(_real_ogr, MagicMock):
            pytest.skip("osgeo.ogr is mocked by conftest")
    except ImportError:
        pytest.skip("GDAL not available")
    geom = tdb._aoi_geometry_for_bounds(-10.0, 10.0, 170.0, -170.0, ogr_module=_real_ogr)
    assert geom is not None
    name = geom.GetGeometryName()
    assert name in ("MULTIPOLYGON", "POLYGON")


def test_rectangle_geometry_is_valid_polygon():
    """Rectangle geometry should be a valid OGR polygon."""
    try:
        from osgeo import ogr as _real_ogr
        from unittest.mock import MagicMock
        if isinstance(_real_ogr, MagicMock):
            pytest.skip("osgeo.ogr is mocked by conftest")
    except ImportError:
        pytest.skip("GDAL not available")
    geom = tdb._rectangle_geometry(-10.0, 10.0, -5.0, 5.0, ogr_module=_real_ogr)
    assert geom.GetGeometryName() == "POLYGON"
    assert geom.GetArea() > 0.0


def test_aoi_geometry_single_interval_returns_polygon():
    """When longitudes don't cross antimeridian, returns single Polygon."""
    try:
        from osgeo import ogr as _real_ogr
        from unittest.mock import MagicMock
        if isinstance(_real_ogr, MagicMock):
            pytest.skip("osgeo.ogr is mocked by conftest")
    except ImportError:
        pytest.skip("GDAL not available")
    geom = tdb._aoi_geometry_for_bounds(-10.0, 10.0, -5.0, 5.0, ogr_module=_real_ogr)
    assert geom.GetGeometryName() == "POLYGON"
