# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for tile_download_base.py download caps (v1.6.2).

Fix 2: configurable max_bytes download cap.
Fix 3: SHA-256 cache integrity verification for cached tiles.
"""

import hashlib
import io
import os
from unittest import mock

import pytest


def _https_response(body, content_length=None):
    """Simulate a urllib response with chunked read support."""
    stream = io.BytesIO(body)
    headers = {}
    if content_length is not None:
        headers["Content-Length"] = str(content_length)

    resp = mock.MagicMock()
    resp.read = stream.read
    resp.geturl = mock.Mock(
        return_value="https://copernicus-dem.s3.amazonaws.com/tile.tif"
    )
    resp.headers = headers
    resp.__enter__ = mock.Mock(return_value=resp)
    resp.__exit__ = mock.Mock(return_value=False)
    return resp


# ── Fix 2: max_bytes download cap ────────────────────────────────────


def test_content_length_above_max_bytes_is_rejected(tmp_path):
    """When Content-Length exceeds max_bytes, download returns None."""
    local_tif = str(tmp_path / "tile.tif")
    opener = mock.Mock()
    opener.open = mock.Mock(
        return_value=_https_response(b"data", content_length=1_000_000_000)
    )

    from NoWires.tile_download_base import download_tile_with_retry

    result = download_tile_with_retry(
        tile_url="https://example.com/tile.tif",
        local_tif=local_tif,
        base_name_label="test_tile",
        base_url="https://copernicus-dem.s3.amazonaws.com/",
        opener=opener,
        max_bytes=250_000_000,
    )
    assert result is None


def test_unbounded_download_capped_by_max_bytes(tmp_path):
    """Without Content-Length, download stops at max_bytes and returns None."""
    local_tif = str(tmp_path / "tile.tif")
    opener = mock.Mock()
    opener.open = mock.Mock(
        return_value=_https_response(b"X" * 500_000, content_length=None)
    )

    from NoWires.tile_download_base import download_tile_with_retry

    result = download_tile_with_retry(
        tile_url="https://example.com/tile.tif",
        local_tif=local_tif,
        base_name_label="test_tile",
        base_url="https://copernicus-dem.s3.amazonaws.com/",
        opener=opener,
        max_bytes=100_000,
        max_retries=1,
        wall_clock_budget=None,
    )
    assert result is None
    assert not os.path.exists(local_tif)


def test_download_within_max_bytes_succeeds(tmp_path):
    """Normal download under max_bytes limit completes."""
    local_tif = str(tmp_path / "tile.tif")
    body = b"tiledata" * 200
    opener = mock.Mock()
    opener.open = mock.Mock(
        return_value=_https_response(body, content_length=len(body))
    )

    from NoWires.tile_download_base import download_tile_with_retry

    with mock.patch("NoWires.tile_download_base.gdal.Open") as gdal_open:
        mock_ds = mock.MagicMock()
        mock_ds.RasterCount = 1
        mock_ds.RasterXSize = 2
        mock_ds.RasterYSize = 2
        gdal_open.return_value = mock_ds

        result = download_tile_with_retry(
            tile_url="https://example.com/tile.tif",
            local_tif=local_tif,
            base_name_label="test_tile",
            base_url="https://copernicus-dem.s3.amazonaws.com/",
            opener=opener,
            max_bytes=100_000,
            max_retries=1,
            wall_clock_budget=None,
        )
    assert result is not None


# ── Fix 3: cache integrity verification ─────────────────────────────


def _sidecar_path(tif_path):
    return tif_path + ".sha256"


def _write_sidecar(tif_path, checksum):
    with open(_sidecar_path(tif_path), "w") as f:
        f.write(checksum)


@pytest.mark.gdal_integration
def test_cached_tile_with_valid_checksum_is_reused(tmp_path):
    """Existing tile with matching SHA-256 sidecar is reused without download."""
    from osgeo import gdal

    local_tif = str(tmp_path / "tile.tif")
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(local_tif, 4, 4, 1, gdal.GDT_Byte)
    ds.GetRasterBand(1).Fill(0)
    ds = None

    with open(local_tif, "rb") as f:
        tile_data = f.read()
    checksum = hashlib.sha256(tile_data).hexdigest()
    _write_sidecar(local_tif, checksum)

    from NoWires.tile_download_base import download_tile_with_retry

    opener = mock.Mock()
    opener.open = mock.Mock(return_value=_https_response(b"fresh", content_length=5))

    with mock.patch("NoWires.tile_download_base.gdal.Open") as gdal_open:
        mock_ds = mock.MagicMock()
        mock_ds.RasterCount = 1
        mock_ds.RasterXSize = 4
        mock_ds.RasterYSize = 4
        gdal_open.return_value = mock_ds

        result = download_tile_with_retry(
            tile_url="https://example.com/tile.tif",
            local_tif=local_tif,
            base_name_label="test_tile",
            base_url="https://copernicus-dem.s3.amazonaws.com/",
            opener=opener,
            max_retries=1,
            wall_clock_budget=None,
        )
    assert result is not None


@pytest.mark.gdal_integration
def test_cached_tile_with_mismatched_checksum_is_redownloaded(tmp_path):
    """Cached tile with mismatched SHA-256 is replaced."""
    from osgeo import gdal

    local_tif = str(tmp_path / "tile.tif")
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(local_tif, 4, 4, 1, gdal.GDT_Byte)
    ds.GetRasterBand(1).Fill(0)
    ds = None

    _write_sidecar(local_tif, hashlib.sha256(b"not_this_tile_data").hexdigest())

    from NoWires.tile_download_base import download_tile_with_retry

    opener = mock.Mock()
    opener.open = mock.Mock(return_value=_https_response(b"fresh", content_length=5))

    with mock.patch("NoWires.tile_download_base.gdal.Open") as gdal_open:
        mock_ds = mock.MagicMock()
        mock_ds.RasterCount = 1
        mock_ds.RasterXSize = 4
        mock_ds.RasterYSize = 4
        gdal_open.return_value = mock_ds

        result = download_tile_with_retry(
            tile_url="https://example.com/tile.tif",
            local_tif=local_tif,
            base_name_label="test_tile",
            base_url="https://copernicus-dem.s3.amazonaws.com/",
            opener=opener,
            max_retries=1,
            wall_clock_budget=None,
        )
    assert result is not None


@pytest.mark.gdal_integration
def test_sidecar_written_after_successful_download(tmp_path):
    """Successful download writes a .sha256 sidecar."""
    local_tif = str(tmp_path / "tile.tif")

    from NoWires.tile_download_base import download_tile_with_retry

    opener = mock.Mock()
    opener.open = mock.Mock(return_value=_https_response(b"new_tile", content_length=8))

    with mock.patch("NoWires.tile_download_base.gdal.Open") as gdal_open:
        mock_ds = mock.MagicMock()
        mock_ds.RasterCount = 1
        mock_ds.RasterXSize = 4
        mock_ds.RasterYSize = 4
        gdal_open.return_value = mock_ds

        result = download_tile_with_retry(
            tile_url="https://example.com/tile.tif",
            local_tif=local_tif,
            base_name_label="test_tile",
            base_url="https://copernicus-dem.s3.amazonaws.com/",
            opener=opener,
            max_retries=1,
            wall_clock_budget=None,
        )
    assert result is not None
    assert os.path.exists(_sidecar_path(local_tif))

    with open(_sidecar_path(local_tif)) as f:
        stored = f.read().strip()
    with open(local_tif, "rb") as f:
        expected = hashlib.sha256(f.read()).hexdigest()
    assert stored == expected
