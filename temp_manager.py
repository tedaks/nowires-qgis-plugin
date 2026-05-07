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
                from .dem_downloader import get_temp_dir
                base_dir = get_temp_dir()
            except Exception:
                pass
        path = tempfile.mkdtemp(prefix="nowires_{}-".format(prefix), dir=base_dir)
        if persistent:
            self._persistent_dirs.append(path)
        else:
            self._dirs.append(path)
        return path

    def add_file(self, path):
        """Register a single file for deletion on cleanup()."""
        self._files.append(path)

    def cleanup(self):
        """Remove all non-persistent temporary directories and registered files."""
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)
        self._dirs.clear()
        for f in self._files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
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
        """Safety net: clean up non-persistent dirs if cleanup() was not called."""
        if self._dirs or self._files:
            logger.warning(
                "TempDirManager.__del__ called with uncleaned resources; "
                "calling cleanup() as safety net. Call cleanup() explicitly "
                "to avoid this warning."
            )
            self.cleanup()