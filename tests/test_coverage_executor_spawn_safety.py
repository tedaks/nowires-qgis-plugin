# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for spawn-mode safety of the coverage pool.

Plain ``multiprocessing.Event()`` cannot be shared between processes via
pickle under the 'spawn' start method (macOS default + Windows + containers).
The error is ``RuntimeError: Condition objects should only be shared between
processes through inheritance``. Under fork (Linux default before Python 3.14)
it worked silently; on macOS QGIS coverage runs fell back to sequential mode
without indication.

The fix uses ``multiprocessing.Manager().Event()``, whose proxy survives
pickling. These source-level contract checks catch a regression to the plain
Event without needing a fork/spawn test harness.
"""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_executor_uses_manager_backed_event():
    src = _source("_coverage_executor.py")
    # Manager().Event() is the spawn-safe shape — the proxy is what gets
    # pickled to workers, not the synchronization primitive itself.
    assert "multiprocessing.Manager() as mgr" in src
    assert "mgr.Event()" in src


def test_executor_does_not_use_plain_multiprocessing_event():
    src = _source("_coverage_executor.py")
    # The plain constructor-pattern form raises under spawn — must stay out
    # of the executor. (The substring may appear in explanatory comments.)
    code_lines = [
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    ]
    code_only = "\n".join(code_lines)
    assert "= multiprocessing.Event()" not in code_only


def test_worker_batch_checks_cancel_at_batch_start():
    """Cancel check moved from per-task to per-batch.

    Each ``cancel_event.is_set()`` is an IPC round-trip under Manager-backed
    Events; checking per-task would cost ~36k IPC calls on a 192² coverage.
    """
    src = _source("coverage_pool.py")
    # The early-return cancel guard at batch start.
    assert "if cancel_event is not None and cancel_event.is_set():" in src
    assert "return []" in src
