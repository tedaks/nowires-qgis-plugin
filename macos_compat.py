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


def _can_spawn(py_exe, env):
    """Verify the given interpreter can actually launch and import stdlib.

    Some QGIS-bundled python binaries (e.g. macOS QGIS-final 4.0.2) have
    ``sys.prefix`` baked to a CI builder path that doesn't exist on the
    user's machine. Invoked without a corrective ``PYTHONHOME``, they
    immediately abort with ``ModuleNotFoundError: No module named 'encodings'``.
    """
    import subprocess
    try:
        result = subprocess.run(
            [py_exe, "-c", "import encodings"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_macos_python_executable():
    """Return a path to a real Python interpreter on macOS, or None.

    On macOS, QGIS sets ``sys.executable`` to the QGIS app launcher binary
    (e.g. ``/Applications/QGIS.app/Contents/MacOS/QGIS``). When ``multiprocessing``
    spawns workers, it runs ``sys.executable``, so each worker boots a
    duplicate QGIS instance instead of a Python interpreter.

    This function locates a real Python interpreter so the caller can pass
    it to :func:`multiprocessing.set_executable`. Each candidate is validated
    with :func:`_can_spawn` so we don't return a binary that can't actually
    boot — common on macOS QGIS-final builds where ``python3.12`` has its
    ``sys.prefix`` baked to a CI builder path.

    The ``NOWIRES_PYTHON_EXE`` env var overrides the default search.
    """
    import sys

    if sys.platform != "darwin":
        return None

    # Build spawn-time env the workers will inherit. Setting PYTHONHOME
    # to the running interpreter's prefix lets a QGIS-bundled Python find
    # its stdlib regardless of whatever the binary has baked in.
    spawn_env = dict(os.environ)
    if "PYTHONHOME" not in spawn_env:
        spawn_env["PYTHONHOME"] = sys.prefix

    candidates: list[str] = []
    override = os.environ.get("NOWIRES_PYTHON_EXE")
    if override:
        candidates.append(override)

    base = getattr(sys, "_base_executable", None)
    if base and base != sys.executable:
        candidates.append(base)

    qgis_macos_dir = os.path.dirname(os.path.abspath(sys.executable))
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    candidates.extend([
        os.path.join(qgis_macos_dir, "bin", "python{}.{}".format(py_major, py_minor)),
        os.path.join(qgis_macos_dir, "bin", "python{}".format(py_major)),
        os.path.join(qgis_macos_dir, "bin", "python"),
        os.path.join(qgis_macos_dir, "python{}.{}".format(py_major, py_minor)),
        os.path.join(qgis_macos_dir, "python{}".format(py_major)),
    ])

    for candidate in candidates:
        if not (os.path.exists(candidate) and os.access(candidate, os.X_OK)):
            continue
        if not _can_spawn(candidate, spawn_env):
            logger.info(
                "macOS: %s exists but fails to spawn even with PYTHONHOME=%s; "
                "trying next candidate.", candidate, spawn_env["PYTHONHOME"])
            continue
        return candidate
    return None


def configure_macos_multiprocessing():
    """Point multiprocessing at a real Python interpreter on macOS.

    Also sets ``PYTHONHOME`` in the process env so spawned workers inherit
    a working stdlib pointer. The macOS QGIS-final python3.12 binary has
    ``sys.prefix`` baked to a CI builder path (``/Users/runner/work/...``)
    and aborts immediately on start without this override.

    No-op on non-macOS platforms.
    """
    import sys

    if sys.platform != "darwin":
        return
    python_exe = find_macos_python_executable()
    if python_exe is None:
        logger.warning(
            "macOS: no usable Python interpreter for multiprocessing. "
            "Coverage will run sequentially. Set NOWIRES_PYTHON_EXE to a "
            "working Python 3 to opt in.")
        return
    multiprocessing.set_executable(python_exe)
    if "PYTHONHOME" not in os.environ:
        os.environ["PYTHONHOME"] = sys.prefix