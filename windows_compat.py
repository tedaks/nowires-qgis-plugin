# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Windows multiprocessing compatibility helpers.

Windows mirror of ``macos_compat``. Windows uses the ``spawn`` start method
natively, so the same family of failures we hit on macOS-bundled Python
(notably PYTHONHOME baked to a builder path) can surface here too. This
module locates a working ``python.exe`` inside a Windows QGIS install,
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

from .macos_compat import _can_spawn

logger = logging.getLogger(__name__)

__all__ = [
    "configure_windows_multiprocessing",
    "find_windows_python_executable",
]


def find_windows_python_executable():
    """Return a path to a working python.exe on Windows, or None.

    Candidates checked in order:
    1. ``NOWIRES_PYTHON_EXE`` env var (explicit override).
    2. ``sys.executable`` if it already ends with ``python.exe``.
    3. ``sys._base_executable`` if distinct from ``sys.executable``.
    4. Common Windows-QGIS bundle layouts relative to ``sys.executable``:
       - ``<dir>/python.exe`` (standalone)
       - ``<dir>/../apps/PythonXY/python.exe`` (OSGeo4W-style)
       - ``<dir>/bin/python.exe``

    Each candidate is validated with ``_can_spawn`` under a prepared env that
    sets ``PYTHONHOME = sys.prefix`` so a python.exe with a baked-in CI
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

    if sys.executable.lower().endswith("python.exe"):
        candidates.append(sys.executable)

    base = getattr(sys, "_base_executable", None)
    if base and base != sys.executable and base.lower().endswith("python.exe"):
        candidates.append(base)

    qgis_dir = os.path.dirname(os.path.abspath(sys.executable))
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    py_xy = "Python{}{}".format(py_major, py_minor)
    py_x = "Python{}".format(py_major)
    candidates.extend([
        os.path.join(qgis_dir, "python.exe"),
        os.path.join(qgis_dir, "..", "apps", py_xy, "python.exe"),
        os.path.join(qgis_dir, "..", "apps", py_x, "python.exe"),
        os.path.join(qgis_dir, "..", py_xy, "python.exe"),
        os.path.join(qgis_dir, "bin", "python.exe"),
    ])

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
