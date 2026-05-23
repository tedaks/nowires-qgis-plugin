# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""SHA-256 cache integrity helpers for tile download verification.

Used by tile_download_base to validate cached tiles and write integrity
sidecars after successful downloads.
"""

import hashlib
import logging
import os

logger = logging.getLogger(__name__)
_SHA256_EXT = ".sha256"


def sidecar_path(tif_path):
    return tif_path + _SHA256_EXT


def cleanup_sidecar(tif_path):
    sidecar = sidecar_path(tif_path)
    try:
        os.unlink(sidecar)
    except OSError:
        pass


def verify_checksum(tif_path):
    sidecar = sidecar_path(tif_path)
    if not os.path.exists(sidecar):
        return False
    try:
        with open(sidecar) as f:
            expected = f.read().strip()
    except OSError:
        return False
    sha256 = hashlib.sha256()
    try:
        with open(tif_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)
    except OSError:
        return False
    return sha256.hexdigest() == expected


def write_checksum(tif_path):
    sha256 = hashlib.sha256()
    with open(tif_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    with open(sidecar_path(tif_path), "w") as f:
        f.write(sha256.hexdigest())


def reject_oversized_content_length(expected_size, max_bytes, base_name_label, feedback):
    """Log and optionally push a warning; return True if the tile is too large."""
    if max_bytes is None or expected_size <= max_bytes:
        return False
    logger.warning("Content-Length %d exceeds max_bytes %d for %s",
                   expected_size, max_bytes, base_name_label)
    if feedback:
        feedback.pushWarning("Tile too large ({} > {} bytes): {}".format(
            expected_size, max_bytes, base_name_label))
    return True


def cap_exceeded(bytes_received, chunk_len, max_bytes, label, file_handle, tmp_path):
    """Flush, unlink tmp, and return True if download cap is exceeded."""
    if max_bytes is None or bytes_received + chunk_len <= max_bytes:
        return False
    logger.warning("Download cap exceeded for %s (%d > %d)",
                   label, bytes_received + chunk_len, max_bytes)
    file_handle.flush()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    return True
