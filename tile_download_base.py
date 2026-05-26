# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
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

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

Shared tile download logic with retry, validation, and caching for DEM and WorldCover downloaders.
"""

import logging
import os
import random
import time
import urllib.error
from urllib.parse import urlsplit, urlunsplit

from osgeo import gdal

from NoWires.tile_cache_integrity import (
    cap_exceeded, cleanup_sidecar, reject_oversized_content_length,
    verify_checksum, write_checksum)

logger = logging.getLogger(__name__)
DEFAULT_PER_TILE_WALL_CLOCK_BUDGET = 180
DEFAULT_MAX_BYTES = 250 * 1024 * 1024


def _redact_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(query="", fragment=""))


def _backoff_seconds(attempt: int) -> float:
    return 2 ** attempt + random.uniform(0, 1)

def download_tile_with_retry(
    tile_url, local_tif, base_name_label, feedback=None,
    max_retries=3, socket_timeout=60, valid_tile_re=None,
    base_url=None, opener=None,
    wall_clock_budget=DEFAULT_PER_TILE_WALL_CLOCK_BUDGET,
    max_bytes=DEFAULT_MAX_BYTES,
):
    if valid_tile_re is not None and not valid_tile_re.match(base_name_label):
        logger.error("Invalid tile name rejected: %s", base_name_label)
        return None

    if os.path.exists(local_tif):
        test_ds = gdal.Open(local_tif)
        if test_ds is not None:
            try:
                band_count = test_ds.RasterCount
                xsize = test_ds.RasterXSize
                ysize = test_ds.RasterYSize
                if xsize > 0 and ysize > 0 and band_count >= 1:
                    if verify_checksum(local_tif):
                        logger.debug("Cache hit: %s (%dx%d)", base_name_label, xsize, ysize)
                        if feedback:
                            feedback.pushInfo("Cache hit: " + base_name_label)
                        return local_tif
                    logger.warning("Cached tile %s checksum mismatch; re-downloading",
                                   base_name_label)
                else:
                    logger.warning("Cached tile %s has degenerate dimensions; re-downloading",
                                   base_name_label)
            finally:
                test_ds = None
        else:
            logger.warning("Cached tile %s failed validation; re-downloading",
                           base_name_label)
        try:
            os.unlink(local_tif)
        except OSError:
            pass
        cleanup_sidecar(local_tif)
    if feedback:
        feedback.pushInfo("Downloading: " + _redact_query(tile_url))
    logger.debug("Downloading full URL: %s", tile_url)
    downloaded = False
    tmp_path = local_tif + ".tmp"
    t_start = time.monotonic()
    for attempt in range(max_retries):
        if feedback and feedback.isCanceled():
            return None
        elapsed = time.monotonic() - t_start
        if wall_clock_budget is not None and elapsed >= wall_clock_budget:
            logger.warning("Wall-clock budget exceeded (%.1f/%.1f s) for %s",
                           elapsed, wall_clock_budget, base_name_label)
            if feedback:
                feedback.pushInfo("Download budget exceeded: " + base_name_label)
            break
        try:
            with opener.open(tile_url, timeout=socket_timeout) as response:
                final_url = response.geturl()
                if base_url is not None:
                    base = urlsplit(base_url)
                    final = urlsplit(final_url)
                    if (final.netloc.lower() != base.netloc.lower()
                            or final.scheme != base.scheme):
                        raise RuntimeError("Unexpected redirect to: " + final_url)
                content_length_hdr = response.headers.get("Content-Length")
                if content_length_hdr is None:
                    expected_size = 0
                else:
                    expected_size = int(content_length_hdr)
                    if reject_oversized_content_length(
                        expected_size, max_bytes, base_name_label, feedback):
                        return None
                bytes_received = 0
                with open(tmp_path, "wb") as f:
                    while True:
                        if feedback and feedback.isCanceled():
                            f.flush()
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass
                            return None
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        if cap_exceeded(bytes_received, len(chunk), max_bytes,
                                        base_name_label, f, tmp_path):
                            return None
                        f.write(chunk)
                        bytes_received += len(chunk)
                    f.flush()
                    os.fsync(f.fileno())

            if expected_size > 0 and bytes_received != expected_size:
                logger.warning("Incomplete download %s: %d/%d bytes",
                               base_name_label, bytes_received, expected_size)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(_backoff_seconds(attempt))
                    continue
                raise ValueError("Incomplete download: {} of {} bytes".format(
                    bytes_received, expected_size))

            test_ds = gdal.Open(tmp_path)
            if test_ds is None:
                logger.warning("Downloaded tile is corrupt: %s", base_name_label)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(_backoff_seconds(attempt))
                    continue
                break
            test_ds = None
            os.replace(tmp_path, local_tif)
            write_checksum(local_tif)
            downloaded = True
            break

        except urllib.error.HTTPError as e:
            retryable_codes = {408, 425, 429}
            if e.code == 404:
                logger.info("Tile not available (404): %s", base_name_label)
                if feedback:
                    feedback.pushInfo("Tile not available (HTTP 404): " + base_name_label)
                break
            elif e.code in retryable_codes or e.code >= 500:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_secs = max(int(retry_after), 1)
                    except ValueError:
                        wait_secs = _backoff_seconds(attempt)
                else:
                    wait_secs = _backoff_seconds(attempt)
                msg = "HTTP {} on {} (attempt {}/{}); retry in {}s".format(
                    e.code, base_name_label, attempt + 1, max_retries, wait_secs)
                logger.warning(msg)
                if feedback:
                    feedback.pushInfo(msg)
                if attempt < max_retries - 1:
                    time.sleep(wait_secs)
            else:
                msg = "HTTP {} on {} (non-retryable)".format(e.code, base_name_label)
                logger.error(msg)
                if feedback:
                    feedback.pushWarning(msg)
                break
        except Exception as e:
            logger.warning("Error downloading %s (attempt %d/%d): %s",
                base_name_label, attempt + 1, max_retries, e)
            if feedback:
                feedback.pushInfo("Error downloading {} (attempt {}): {}".format(
                    base_name_label, attempt + 1, str(e)))
            if attempt < max_retries - 1:
                time.sleep(_backoff_seconds(attempt))

    if not downloaded and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return local_tif if downloaded else None
