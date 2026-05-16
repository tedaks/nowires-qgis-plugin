# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for spawn-mode safety of the coverage pool.

History of attempted cross-process cancel signals:

  1. Plain ``multiprocessing.Event()`` — fails under spawn (macOS default,
     Windows, containers) with ``RuntimeError: Condition objects should only
     be shared between processes through inheritance``. Linux fork worked.

  2. ``multiprocessing.Manager().Event()`` — Manager subprocess died on
     macOS QGIS, surfacing as ``EOFError`` on the first ``mgr.Event()`` call.

Current design: no cross-process cancel signal. Cancellation comes from the
main thread breaking out of ``pool.map`` between batches; in-flight batches
finish (~64 tasks × ~5 ms ≈ 320 ms worst-case at default chunk size). These
source-level contract checks guard the pool against regressing to either of
the broken patterns above.
"""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def _code_only(name):
    """Return source with comment lines stripped (substring checks vs. code)."""
    return "\n".join(
        line for line in _source(name).splitlines()
        if not line.lstrip().startswith("#")
    )


def test_executor_does_not_use_plain_multiprocessing_event():
    code = _code_only("_coverage_executor.py")
    assert "= multiprocessing.Event()" not in code


def test_executor_does_not_use_manager_event():
    """Manager().Event() died on macOS QGIS with EOFError."""
    code = _code_only("_coverage_executor.py")
    assert "multiprocessing.Manager()" not in code
    assert ".Event()" not in code or "multiprocessing.Event" in code, \
        "no .Event() call should remain in the executor"


def test_worker_batch_takes_plain_chunk_argument():
    """_itm_worker_batch must accept a plain batch arg, not a (batch, event) tuple."""
    code = _code_only("coverage_pool.py")
    # The function signature is now `def _itm_worker_batch(batch):`
    assert "def _itm_worker_batch(batch):" in code
    # And the cancel-event check is gone.
    assert "cancel_event.is_set()" not in code
