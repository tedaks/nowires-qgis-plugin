# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""DEM and WorldCover tile cache management utilities."""

import glob as _glob
import os
import shutil

from .dem_downloader import get_temp_dir

_DEM_PATTERNS = (
    "Copernicus_DSM_COG_*.tif",
    "merged_dem*.tif",
    "nowires_dem_*",
    "nowires_worldcover_*",
)
_WC_PATTERNS = ("ESA_WorldCover*.tif", "merged_worldcover*.tif")


def _entry_size(entry):
    if os.path.isdir(entry):
        return sum(
            os.path.getsize(os.path.join(dp, fn))
            for dp, _, fns in os.walk(entry)
            for fn in fns
        )
    return os.path.getsize(entry)


def _iter_cache_entries():
    temp_dir = get_temp_dir()
    if not os.path.isdir(temp_dir):
        return
    for pat in _DEM_PATTERNS:
        for entry in _glob.glob(os.path.join(temp_dir, pat)):
            yield entry
    wc_dir = os.path.join(temp_dir, "worldcover")
    if os.path.isdir(wc_dir):
        for pat in _WC_PATTERNS:
            for entry in _glob.glob(os.path.join(wc_dir, pat)):
                yield entry


def get_cache_size():
    """Return (file_count, total_bytes) for the on-disk DEM + WorldCover cache."""
    count = 0
    total = 0
    for entry in _iter_cache_entries():
        try:
            total += _entry_size(entry)
            count += 1
        except OSError:
            pass
    return count, total


def clear_dem_cache(feedback=None):
    """Remove all cached DEM and WorldCover tiles from the temp directory.

    Returns ``(removed_file_count, freed_bytes_approx)``.
    """
    removed = 0
    freed_bytes = 0
    for entry in _iter_cache_entries():
        try:
            size = _entry_size(entry)
            if os.path.isdir(entry):
                shutil.rmtree(entry, ignore_errors=True)
            else:
                os.unlink(entry)
            freed_bytes += size
            removed += 1
        except OSError:
            pass
    if feedback:
        feedback.pushInfo(
            "NoWires: removed {} cached tile file(s), freed ~{:.1f} MB".format(
                removed, freed_bytes / 1048576.0
            )
        )
    return removed, freed_bytes


def format_cache_size(file_count, total_bytes):
    """Human-readable summary used by UI confirmation prompts."""
    if file_count == 0:
        return "Cache is empty."
    mb = total_bytes / 1048576.0
    return "Cache: {} file(s), ~{:.1f} MB.".format(file_count, mb)
