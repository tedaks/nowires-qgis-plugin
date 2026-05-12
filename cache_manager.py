# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""DEM and WorldCover tile cache management utilities."""

import glob as _glob
import os
import shutil

from .dem_downloader import get_temp_dir

def clear_dem_cache(feedback=None):
    """Remove all cached DEM tiles from the temp directory.

    Iterates the NoWires temp directory and deletes GLO-30 tile files
    (*.tif) and merge artifacts left by previous runs. WorldCover tiles
    are also removed if present in the worldcover subdirectory.

    Returns a tuple of (removed_file_count, freed_bytes_approx).
    """
    import glob as _glob
    import shutil

    temp_dir = get_temp_dir()
    if not os.path.isdir(temp_dir):
        return 0, 0

    removed = 0
    freed_bytes = 0

    # Remove GLO-30 tile files and merge outputs
    patterns = [
        "Copernicus_DSM_COG_*.tif",
        "merged_dem*.tif",
        "nowires_dem_*",
        "nowires_worldcover_*",
    ]
    for pat in patterns:
        for entry in _glob.glob(os.path.join(temp_dir, pat)):
            try:
                if os.path.isdir(entry):
                    s = sum(
                        os.path.getsize(os.path.join(dp, fn))
                        for dp, _, fns in os.walk(entry)
                        for fn in fns
                    )
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    s = os.path.getsize(entry)
                    os.unlink(entry)
                freed_bytes += s
                removed += 1
            except OSError:
                pass

    # Remove worldcover subdirectory contents
    wc_dir = os.path.join(temp_dir, "worldcover")
    if os.path.isdir(wc_dir):
        for entry in _glob.glob(os.path.join(wc_dir, "ESA_WorldCover*.tif")):
            try:
                s = os.path.getsize(entry)
                os.unlink(entry)
                freed_bytes += s
                removed += 1
            except OSError:
                pass
        for entry in _glob.glob(os.path.join(wc_dir, "merged_worldcover*.tif")):
            try:
                s = os.path.getsize(entry)
                os.unlink(entry)
                freed_bytes += s
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
