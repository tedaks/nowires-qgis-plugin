# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-level + behavioral tests for the Windows multiprocessing helper.

The on-machine validation path can't be exercised from a non-Windows test
machine (``find_windows_python_executable`` returns None early because
``os.name != "nt"``). What we CAN test here:

  * the helper mirrors the macOS shape (`PYTHONHOME` is set, `_can_spawn`
    is used, an `NOWIRES_PYTHON_EXE` override is honored);
  * on non-Windows hosts the helper short-circuits to None — so the existing
    contract "Windows MP is off in the unit test environment" still holds.
"""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_find_windows_python_returns_none_on_non_windows():
    """The early gate keeps the function safe to import everywhere."""
    from NoWires.windows_compat import find_windows_python_executable
    if os.name == "nt":  # pragma: no cover - non-Windows test harness
        return
    assert find_windows_python_executable() is None


def test_configure_windows_is_noop_off_windows():
    """configure_windows_multiprocessing must be a no-op on non-Windows."""
    from NoWires.windows_compat import configure_windows_multiprocessing
    if os.name == "nt":  # pragma: no cover - non-Windows test harness
        return
    configure_windows_multiprocessing()  # must not raise


def test_windows_compat_sets_pythonhome_for_spawned_workers():
    src = _source("windows_compat.py")
    assert 'spawn_env["PYTHONHOME"] = sys.prefix' in src
    assert 'os.environ["PYTHONHOME"] = sys.prefix' in src


def test_windows_compat_validates_each_candidate_with_can_spawn():
    src = _source("windows_compat.py")
    assert "from NoWires.macos_compat import _can_spawn" in src
    assert "_can_spawn(candidate, spawn_env)" in src


def test_windows_compat_honors_override_env_var():
    src = _source("windows_compat.py")
    assert 'os.environ.get("NOWIRES_PYTHON_EXE")' in src


def test_executor_calls_configure_windows():
    src = _source("radio_coverage/_executor.py")
    assert "configure_windows_multiprocessing" in src


def test_should_use_multiprocessing_consults_windows_helper():
    src = _source("radio_coverage/pool.py")
    assert "find_windows_python_executable" in src


def test_windows_compat_prefers_pythonw_over_python_exe():
    """python.exe is a console binary and spawning it pops a stray cmd window
    for each worker. pythonw.exe is the windowless interpreter — same binary
    semantics over pipes, no console.
    """
    src = _source("windows_compat.py")
    # Both must appear; pythonw.exe must appear FIRST in the source (earlier
    # in the candidate-building code path).
    py_idx = src.find('"python.exe"')
    pyw_idx = src.find('"pythonw.exe"')
    assert pyw_idx > 0, "windows_compat.py must reference pythonw.exe"
    assert py_idx > 0, "windows_compat.py must still fall back to python.exe"
    assert pyw_idx < py_idx, (
        "pythonw.exe must be tried before python.exe to avoid stray cmd "
        "windows on Windows")
