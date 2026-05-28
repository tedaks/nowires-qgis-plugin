# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared helper for project-relative output directory resolution."""

import os


def _project_or_temp_dir(tmp_mgr, context, feedback, name):
    """Resolve a file output directory relative to the project, or fall back to temp.

    When a QGIS project is saved (``context.project().fileName()`` is non-empty),
    creates ``<project_dir>/nowires_<name>/`` so temporary layers survive reboot
    and cross-machine transfer (when QGIS "Save paths as relative" is enabled).
    Otherwise falls back to the existing ``/tmp``-based TempDirManager behavior.
    """
    proj = context.project().fileName()
    if proj:
        out = os.path.join(os.path.dirname(proj), "nowires_" + name)
        os.makedirs(out, exist_ok=True)
        return out
    out = tmp_mgr.make_dir(name, persistent=True)
    tmp_mgr.warn_persistent(feedback)
    return out
