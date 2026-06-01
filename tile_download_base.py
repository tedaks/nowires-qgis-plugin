# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
        email                : tedaks@gmail.com
 ***************************************************************************/

 Licensed under the MIT License; see the LICENSE file for the full text.


Generic HTTP tile downloader with retry, caching, and integrity validation.

Shared by ``dem_downloader`` and ``worldcover_downloader``. Fetches a single
remote GeoTIFF over HTTPS into an on-disk cache, validating it with GDAL and a
SHA-256 sidecar, and retrying transient failures with exponential backoff.

This module is original work written from standard HTTP-client policy, the
public call signature (``worldcover_downloader.py``), and the project's own
tests (see CLEANROOM.md); see NOTICE.md for attribution.
"""

from __future__ import annotations

import logging
import os
import random
import time
import urllib.error
from urllib.parse import urlsplit

from osgeo import gdal

from NoWires.tile_cache_integrity import (
    cap_exceeded,
    cleanup_sidecar,
    reject_oversized_content_length,
    verify_checksum,
    write_checksum,
)

logger = logging.getLogger(__name__)

DEFAULT_PER_TILE_WALL_CLOCK_BUDGET = 180
DEFAULT_MAX_BYTES = 250 * 1024 * 1024
_DEFAULT_RETRIES = 3
_DEFAULT_SOCKET_TIMEOUT = 60
_CHUNK_SIZE = 65536

# Actions returned by _classify_http_error.
_GIVE_UP = "give_up"
_RETRY_AFTER = "retry_after"
_RETRY_BACKOFF = "retry_backoff"

# Transient HTTP statuses worth retrying; everything else 4xx is terminal.
_RETRYABLE_STATUS = (408, 425, 429)


def _redact_query(url: str) -> str:
    """Drop the query and fragment from *url* so signed URLs are log-safe."""
    parts = urlsplit(url)
    return "{}://{}{}".format(parts.scheme, parts.netloc, parts.path) if parts.scheme \
        else parts.path


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with full jitter: [2**attempt, 2**attempt + 1)."""
    return (2.0 ** attempt) + random.random()


def _classify_http_error(error, attempt):
    """Map a download exception to (action, wait_seconds)."""
    if isinstance(error, urllib.error.HTTPError):
        code = error.code
        if code not in _RETRYABLE_STATUS and code < 500:
            return (_GIVE_UP, 0.0)
        retry_after = None
        if error.headers:
            retry_after = error.headers.get("Retry-After")
        if retry_after:
            try:
                return (_RETRY_AFTER, float(retry_after))
            except (TypeError, ValueError):
                pass
        return (_RETRY_BACKOFF, _backoff_seconds(attempt))
    return (_RETRY_BACKOFF, _backoff_seconds(attempt))


def _structurally_valid(path):
    """Return True when GDAL opens *path* with at least one non-degenerate band."""
    ds = gdal.Open(path)
    if ds is None:
        return False
    valid = ds.RasterCount >= 1 and ds.RasterXSize > 0 and ds.RasterYSize > 0
    ds = None
    return bool(valid)


def _validate_downloaded_tile(tmp_path):
    """Return True when a freshly downloaded tile opens (GDAL can read it)."""
    return gdal.Open(tmp_path) is not None


def _serve_from_cache(local_tif, base_name_label, feedback):
    """Return *local_tif* if a structurally valid, checksum-verified cache exists.

    Tolerates ComputeStatistics failures (structural validity is sufficient).
    A present-but-invalid cache file is purged so it can be re-downloaded.
    """
    if not os.path.exists(local_tif):
        return None
    if _structurally_valid(local_tif) and verify_checksum(local_tif):
        if feedback:
            feedback.pushInfo("Cache hit: " + base_name_label)
        return local_tif
    _cleanup_tmp(local_tif)
    cleanup_sidecar(local_tif)
    return None


def _cleanup_tmp(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _download_to_tmp(opener, tile_url, tmp_path, base_url, socket_timeout,
                     max_bytes, base_name_label, feedback):
    """Stream *tile_url* into *tmp_path*; return (bytes_received, expected_size).

    Returns (None, expected) on cancel, a cross-host/scheme redirect, or an
    oversized Content-Length.
    """
    with opener.open(tile_url, timeout=socket_timeout) as response:
        if base_url:
            final = urlsplit(response.geturl())
            origin = urlsplit(base_url)
            if final.netloc != origin.netloc or final.scheme != origin.scheme:
                if feedback:
                    feedback.pushInfo(
                        "Rejected redirect to a different host: "
                        + _redact_query(response.geturl()))
                return (None, None)

        expected = None
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                expected = int(content_length)
            except (TypeError, ValueError):
                expected = None
        if expected is not None and reject_oversized_content_length(
                expected, max_bytes, base_name_label, feedback):
            return (None, expected)

        bytes_received = 0
        with open(tmp_path, "wb") as handle:
            while True:
                if feedback and feedback.isCanceled():
                    return (None, expected)
                chunk = response.read(_CHUNK_SIZE)
                if not chunk:
                    break
                if cap_exceeded(bytes_received, len(chunk), max_bytes,
                                base_name_label, handle, tmp_path):
                    return (None, expected)
                handle.write(chunk)
                bytes_received += len(chunk)
        return (bytes_received, expected)


def download_tile_with_retry(
    tile_url, local_tif, base_name_label, feedback=None,
    max_retries=_DEFAULT_RETRIES, socket_timeout=_DEFAULT_SOCKET_TIMEOUT,
    valid_tile_re=None, base_url=None, opener=None,
    max_bytes=DEFAULT_MAX_BYTES,
    wall_clock_budget=DEFAULT_PER_TILE_WALL_CLOCK_BUDGET,
):
    """Download a single tile into *local_tif*, returning its path or None.

    Serves a valid cached copy without any network access; otherwise downloads
    to a ``.tmp`` sibling, validates it, and atomically promotes it. Transient
    HTTP/connection failures are retried with backoff (honoring Retry-After);
    404/4xx terminal errors and cross-host redirects are not retried.
    """
    if valid_tile_re is not None and not valid_tile_re.match(base_name_label):
        logger.warning("Rejecting unsafe tile name: %s", base_name_label)
        return None

    if feedback and feedback.isCanceled():
        return None

    cached = _serve_from_cache(local_tif, base_name_label, feedback)
    if cached is not None:
        return cached

    tmp_path = local_tif + ".tmp"
    start = time.monotonic()

    for attempt in range(max_retries):
        if feedback:
            feedback.pushInfo("Downloading: " + _redact_query(tile_url))
        if wall_clock_budget is not None and time.monotonic() - start >= wall_clock_budget:
            if feedback:
                feedback.pushInfo("Download budget exceeded: " + base_name_label)
            return None

        try:
            bytes_received, expected = _download_to_tmp(
                opener, tile_url, tmp_path, base_url, socket_timeout,
                max_bytes, base_name_label, feedback)
        except Exception as error:  # noqa: BLE001 - classified below
            _cleanup_tmp(tmp_path)
            action, wait = _classify_http_error(error, attempt)
            if action == _GIVE_UP:
                if isinstance(error, urllib.error.HTTPError) and feedback:
                    if error.code == 404:
                        feedback.pushInfo(
                            "Tile not available (HTTP 404): " + base_name_label)
                    else:
                        feedback.pushInfo(
                            "Non-retryable HTTP {} error for {}".format(
                                error.code, base_name_label))
                return None
            if attempt < max_retries - 1:
                time.sleep(wait)
                continue
            return None

        if bytes_received is None:
            _cleanup_tmp(tmp_path)
            return None

        if expected is not None and bytes_received != expected:
            logger.warning("Incomplete download for %s (%d of %d bytes)",
                           base_name_label, bytes_received, expected)
            _cleanup_tmp(tmp_path)
            if attempt < max_retries - 1:
                time.sleep(_backoff_seconds(attempt))
                continue
            return None

        if not _validate_downloaded_tile(tmp_path):
            logger.warning("Downloaded tile failed validation: %s", base_name_label)
            _cleanup_tmp(tmp_path)
            if attempt < max_retries - 1:
                time.sleep(_backoff_seconds(attempt))
                continue
            return None

        os.replace(tmp_path, local_tif)
        try:
            write_checksum(local_tif)
        except OSError:
            logger.debug("Could not write checksum sidecar for %s", local_tif)
        return local_tif

    return None
