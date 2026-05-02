# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
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


Shared tile download logic with retry, validation, and caching.

Provides download_tile_with_retry for use by DEM and WorldCover downloaders.
"""

import logging
import os
import time
import urllib.error

from osgeo import gdal

logger = logging.getLogger(__name__)


def download_tile_with_retry(
    tile_url,
    local_tif,
    base_name_label,
    feedback=None,
    max_retries=3,
    socket_timeout=60,
    valid_tile_re=None,
    base_url=None,
    opener=None,
):
    if valid_tile_re is not None and not valid_tile_re.match(base_name_label):
        logger.error("Invalid tile name rejected: %s", base_name_label)
        return None

    if os.path.exists(local_tif):
        if gdal.Open(local_tif) is not None:
            logger.debug("Cache hit: %s", base_name_label)
            if feedback:
                feedback.pushInfo("Cache hit: " + base_name_label)
            return local_tif
        logger.warning(
            "Cached tile %s failed validation; re-downloading", base_name_label
        )
        try:
            os.unlink(local_tif)
        except OSError:
            pass

    if feedback:
        feedback.pushInfo("Downloading: " + tile_url)

    downloaded = False
    tmp_path = local_tif + ".tmp"

    for attempt in range(max_retries):
        if feedback and feedback.isCanceled():
            return None
        try:
            with opener.open(tile_url, timeout=socket_timeout) as response:
                final_url = response.geturl()
                if base_url is not None and not final_url.startswith(base_url):
                    raise RuntimeError("Unexpected redirect to: " + final_url)
                expected_size = int(response.headers.get("Content-Length", 0))
                bytes_received = 0
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)

            if expected_size > 0 and bytes_received != expected_size:
                logger.warning(
                    "Incomplete download %s: %d/%d bytes",
                    base_name_label,
                    bytes_received,
                    expected_size,
                )
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise ValueError(
                    "Incomplete download: {} of {} bytes".format(
                        bytes_received, expected_size
                    )
                )

            test_ds = gdal.Open(tmp_path)
            if test_ds is None:
                logger.warning("Downloaded tile is corrupt: %s", base_name_label)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                break
            test_ds = None

            os.replace(tmp_path, local_tif)
            downloaded = True
            break

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info("Tile not available (404): %s", base_name_label)
                if feedback:
                    feedback.pushInfo(
                        "Tile not available (HTTP 404): " + base_name_label
                    )
                break
            else:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_secs = max(int(retry_after), 1)
                    except ValueError:
                        wait_secs = 2 ** attempt
                    logger.info(
                        "HTTP %d downloading %s — Retry-After: %ds (attempt %d/%d)",
                        e.code,
                        base_name_label,
                        wait_secs,
                        attempt + 1,
                        max_retries,
                    )
                else:
                    wait_secs = 2 ** attempt
                logger.warning(
                    "HTTP %d downloading %s (attempt %d/%d): %s",
                    e.code,
                    base_name_label,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    time.sleep(wait_secs)
        except Exception as e:
            logger.warning(
                "Error downloading %s (attempt %d/%d): %s",
                base_name_label,
                attempt + 1,
                max_retries,
                e,
            )
            if feedback:
                feedback.pushInfo(
                    "Error downloading {} (attempt {}): {}".format(
                        base_name_label, attempt + 1, str(e)
                    )
                )
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    if not downloaded and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return local_tif if downloaded else None