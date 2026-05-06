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


macOS multiprocessing compatibility helpers.

On macOS (spawn start method), QGIS sets sys.executable to the app launcher
binary, which opens a duplicate QGIS GUI when multiprocessing spawns workers.
These helpers locate a real Python interpreter and configure multiprocessing
to use it instead.
"""

import logging
import multiprocessing
import os

logger = logging.getLogger(__name__)

__all__ = [
    "configure_macos_multiprocessing",
    "ensure_spawn_start_method",
    "find_macos_python_executable",
    "is_subprocess",
]


def is_subprocess():
    """Return True if running in a multiprocessing worker process."""
    return multiprocessing.current_process().name != "MainProcess"


def ensure_spawn_start_method():
    """Explicitly set 'spawn' start method on macOS.

    macOS defaults to spawn, but another plugin or user code may have
    changed the method.  Forcing spawn ensures child processes do not
    inherit dangerous state and the ``_NoOpPlugin`` guard works correctly.
    """
    import sys

    if sys.platform == "darwin":
        try:
            multiprocessing.set_start_method("spawn", force=True)
        except RuntimeError:
            pass


def find_macos_python_executable():
    """Return a path to a real Python interpreter on macOS, or None.

    On macOS, QGIS sets ``sys.executable`` to the QGIS app launcher binary
    (e.g. ``/Applications/QGIS.app/Contents/MacOS/QGIS``).  The launcher
    ignores ``-c`` and similar Python flags and instead opens a full
    QGIS GUI window.  When ``multiprocessing`` spawns workers, it runs
    ``sys.executable``, so each worker boots a duplicate QGIS instance
    instead of a Python interpreter.

    This function locates a real Python interpreter so the caller can
    pass it to :func:`multiprocessing.set_executable`.
    """
    import sys

    if sys.platform != "darwin":
        return None

    base = getattr(sys, "_base_executable", None)
    if base and base != sys.executable and os.path.exists(base):
        return base

    qgis_macos_dir = os.path.dirname(os.path.abspath(sys.executable))
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    candidates = [
        os.path.join(qgis_macos_dir, "bin", "python{}.{}".format(py_major, py_minor)),
        os.path.join(qgis_macos_dir, "bin", "python{}".format(py_major)),
        os.path.join(qgis_macos_dir, "bin", "python"),
        os.path.join(qgis_macos_dir, "python{}.{}".format(py_major, py_minor)),
        os.path.join(qgis_macos_dir, "python{}".format(py_major)),
    ]
    for candidate in candidates:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def configure_macos_multiprocessing():
    """Point multiprocessing at a real Python interpreter on macOS.

    No-op on non-macOS platforms.  See
    :func:`find_macos_python_executable` for context on why this is
    needed.
    """
    import sys

    if sys.platform != "darwin":
        return
    python_exe = find_macos_python_executable()
    if python_exe is None:
        logger.warning(
            "Could not locate a Python interpreter for multiprocessing on macOS; "
            "spawn workers may relaunch the QGIS GUI."
        )
        return
    multiprocessing.set_executable(python_exe)