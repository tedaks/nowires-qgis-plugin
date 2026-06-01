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


Temporary directory lifecycle manager for NoWires algorithms.

Provides ``TempDirManager`` which creates temporary directories on demand
and cleans them up when the algorithm finishes.  Directories intended for
QGIS layer loading are marked as persistent (not auto-cleaned) but tracked
for stale-directory warning on plugin startup.
"""

import logging
import os
import shutil
import tempfile

from NoWires.constants import DIR_PERMISSIONS

logger = logging.getLogger(__name__)


class TempDirManager:
    """Create and manage temporary directories for a single algorithm run.

    Usage::

        mgr = TempDirManager()
        tif_dir = mgr.make_dir("coverage_prx")
        ...
        mgr.cleanup()          # delete non-persistent dirs
        mgr.warn_persistent()  # log persistent dirs left for QGIS

    Integrates with QGIS feedback for progress logging.
    """

    def __init__(self):
        self._dirs = []
        self._persistent_dirs = []
        self._files = []
        self._rmtree = shutil.rmtree
        self._unlink = os.unlink
        self._exists = os.path.exists

    def make_dir(self, prefix, persistent=False):
        """Create a temporary directory and register it for later cleanup.

        Args:
            prefix: Filesystem prefix for the temp dir name.
            persistent: If True, the dir is kept after cleanup() and only
                logged as a persistent output for QGIS layer loading.

        Returns:
            Absolute path to the created directory.
        """
        import sys
        base_dir = None
        if persistent and sys.platform == "darwin":
            try:
                from NoWires.dem_downloader import get_temp_dir
                base_dir = get_temp_dir()
            except Exception as exc:
                logger.debug("macOS persistent temp dir: %s", exc)
        path = tempfile.mkdtemp(prefix="nowires_{}-".format(prefix), dir=base_dir)
        if sys.platform != "win32":
            try:
                os.chmod(path, DIR_PERMISSIONS)
            except OSError:
                pass
        if persistent:
            self._persistent_dirs.append(path)
        else:
            self._dirs.append(path)
        return path

    def add_file(self, path):
        """Register a single file for deletion on cleanup()."""
        self._files.append(path)

    def add_dir(self, path, persistent=False):
        """Register an existing directory for lifecycle tracking.

        Args:
            path: Absolute path to the directory.
            persistent: If True, kept after cleanup() and only logged via
                warn_persistent() (not auto-deleted).
        """
        if persistent:
            self._persistent_dirs.append(path)
        else:
            self._dirs.append(path)

    def cleanup(self):
        """Remove all non-persistent temporary directories and registered files."""
        for d in self._dirs:
            self._rmtree(d, ignore_errors=True)
        self._dirs.clear()
        for f in self._files:
            try:
                if self._exists(f):
                    self._unlink(f)
            except OSError:
                pass
        self._files.clear()

    def warn_persistent(self, feedback=None):
        """Log persistent directories that remain on disk for QGIS layer loading.

        Args:
            feedback: Optional QGIS processing feedback object.
        """
        for d in self._persistent_dirs:
            msg = "Persistent temp dir for QGIS layer loading: {}".format(d)
            logger.info(msg)
            if feedback is not None:
                feedback.pushInfo(msg)

    def __del__(self):
        try:
            if self._dirs or self._files:
                self.cleanup()
        except (TypeError, AttributeError):
            pass
