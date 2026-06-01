# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Windows multiprocessing compatibility helpers.

Windows mirror of ``macos_compat``. Windows uses the ``spawn`` start method
natively, so the same family of failures we hit on macOS-bundled Python
(notably PYTHONHOME baked to a builder path) can surface here too. This
module locates a working ``pythonw.exe`` (or ``python.exe``) inside a Windows QGIS install,
validates that it actually launches, and prepares the env so spawned
workers find the QGIS-bundled stdlib.

Until v1.5.5 the Windows multiprocessing path was disabled by an env-var
opt-in (``NOWIRES_WINDOWS_MP=1``) because we hadn't validated it. With
the validating helper in place, the gate becomes self-adjusting: if
``find_windows_python_executable()`` returns a working interpreter,
multiprocessing is on; otherwise it falls back to sequential.
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import sys

from NoWires.macos_compat import _can_spawn

logger = logging.getLogger(__name__)

__all__ = [
    "configure_windows_multiprocessing",
    "find_windows_python_executable",
]


def find_windows_python_executable():
    """Return a path to a working ``pythonw.exe`` (preferred) or ``python.exe``.

    ``pythonw.exe`` is the windowless variant of the same interpreter; using
    it avoids the stray console window that each spawned worker would open
    when launched from a console-subsystem ``python.exe``.

    Candidates checked in order:
    1. ``NOWIRES_PYTHON_EXE`` env var (explicit override; any extension).
    2. ``<bundle dirs>/pythonw.exe`` across common Windows-QGIS layouts:
       ``<dir>/``, ``<dir>/../apps/PythonXY/``, ``<dir>/bin/`` etc.
    3. ``sys.executable`` / ``sys._base_executable`` if they end in
       ``python(w).exe``.
    4. ``<bundle dirs>/python.exe`` as last-resort fallback.

    Each candidate is validated with ``_can_spawn`` under a prepared env that
    sets ``PYTHONHOME = sys.prefix`` so an interpreter with a baked-in CI
    ``sys.prefix`` can still find its stdlib.
    """
    if os.name != "nt":
        return None

    spawn_env = dict(os.environ)
    if "PYTHONHOME" not in spawn_env:
        spawn_env["PYTHONHOME"] = sys.prefix

    candidates: list[str] = []
    override = os.environ.get("NOWIRES_PYTHON_EXE")
    if override:
        candidates.append(override)

    # Prefer pythonw.exe (windowless) over python.exe — python.exe is a
    # console subsystem binary and each spawned worker pops a stray cmd
    # window. pythonw.exe is the same interpreter without a console; stdin/
    # stdout/stderr still work over pipes, which is all multiprocessing uses.
    qgis_dir = os.path.dirname(os.path.abspath(sys.executable))
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    py_xy = "Python{}{}".format(py_major, py_minor)
    py_x = "Python{}".format(py_major)
    bundle_dirs = [
        qgis_dir,
        os.path.join(qgis_dir, "..", "apps", py_xy),
        os.path.join(qgis_dir, "..", "apps", py_x),
        os.path.join(qgis_dir, "..", py_xy),
        os.path.join(qgis_dir, "bin"),
    ]
    for d in bundle_dirs:
        candidates.append(os.path.join(d, "pythonw.exe"))
    # Then sys.executable / _base_executable if they're already python(w).exe.
    for path in (sys.executable, getattr(sys, "_base_executable", None)):
        if path and path.lower().endswith(("pythonw.exe", "python.exe")):
            candidates.append(path)
    # Finally fall back to console python.exe in the same bundle dirs.
    for d in bundle_dirs:
        candidates.append(os.path.join(d, "python.exe"))

    for candidate in candidates:
        candidate = os.path.normpath(candidate)
        if not (os.path.exists(candidate) and os.access(candidate, os.X_OK)):
            continue
        if not _can_spawn(candidate, spawn_env):
            logger.info(
                "Windows: %s exists but fails to spawn even with "
                "PYTHONHOME=%s; trying next candidate.",
                candidate, spawn_env["PYTHONHOME"])
            continue
        return candidate
    return None


def configure_windows_multiprocessing():
    """Point multiprocessing at a working python.exe on Windows.

    Mirrors ``configure_macos_multiprocessing``: sets ``PYTHONHOME`` in the
    process env so spawned workers inherit a working stdlib pointer.

    No-op on non-Windows platforms.
    """
    if os.name != "nt":
        return
    python_exe = find_windows_python_executable()
    if python_exe is None:
        logger.warning(
            "Windows: no usable Python interpreter for multiprocessing. "
            "Coverage will run sequentially. Set NOWIRES_PYTHON_EXE to a "
            "working Python 3 to opt in.")
        return
    multiprocessing.set_executable(python_exe)
    if "PYTHONHOME" not in os.environ:
        os.environ["PYTHONHOME"] = sys.prefix
