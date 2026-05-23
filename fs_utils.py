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


File-system utilities for safe directory creation and path handling.
"""

from __future__ import annotations

import logging
import os
import stat
import tempfile

from NoWires.constants import DIR_PERMISSIONS

logger = logging.getLogger(__name__)


def safe_create_dir(target):
    """Create or validate a directory safely, avoiding symlink TOCTOU races.

    Uses tempfile.mkdtemp() for atomic creation when the directory does not
    yet exist. On platforms that support O_DIRECTORY | O_NOFOLLOW, also uses
    os.open to verify an existing directory is not a symlink.
    """
    try:
        st = os.lstat(target)
        if stat.S_ISLNK(st.st_mode):
            logger.warning("Removing symlink at %s", target)
            os.unlink(target)
        elif not os.path.isdir(target):
            logger.warning("Removing non-directory at %s", target)
            os.unlink(target)
        else:
            dir_flag = getattr(os, "O_DIRECTORY", None)
            nofollow_flag = getattr(os, "O_NOFOLLOW", None)
            if dir_flag is not None and nofollow_flag is not None:
                try:
                    fd = os.open(target, os.O_RDONLY | dir_flag | nofollow_flag)
                    os.close(fd)
                except OSError:
                    logger.warning("Removing unsafe directory at %s", target)
                    os.unlink(target)
    except OSError:
        pass
    if not os.path.isdir(target):
        parent = os.path.dirname(target)
        tmp = tempfile.mkdtemp(dir=parent)
        try:
            os.chmod(tmp, DIR_PERMISSIONS)
        except OSError:
            pass
        try:
            os.rename(tmp, target)
        except OSError:
            logger.debug("Could not rename %s to %s; using temp path", tmp, target)
            return tmp
    try:
        st = os.stat(target)
        if st.st_mode & 0o777 != DIR_PERMISSIONS:
            os.chmod(target, DIR_PERMISSIONS)
    except OSError:
        pass
    return target
