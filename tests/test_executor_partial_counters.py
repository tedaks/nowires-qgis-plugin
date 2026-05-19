# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Source-level contract test for partial counter accumulation (v1.5.7 fix #8).

Before v1.5.7, _coverage_executor.execute_coverage_tasks overwrote
pixels_failed/pixels_done with the sequential fallback values, discarding
any partial progress from the multiprocessing phase. The fix accumulates
(+=) instead of overwriting (=).

This test verifies the source code pattern, since the executor requires
a full multiprocessing environment to test end-to-end.
"""

import ast
import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "coverage/_executor.py"))


def test_sequential_fallback_accumulates_not_overwrites():
    """The sequential fallback must use +=, not =, for pixels_failed and pixels_done."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute_coverage_tasks":
            body_src = ast.unparse(node)
            # Must NOT have: cancelled, pixels_failed, pixels_done = _run_sequential(...)
            assert "pixels_failed +=" in body_src or "_run_sequential" not in body_src, (
                "After MP fallback, pixels_failed must be accumulated (+=), "
                "not overwritten (=)"
            )
            assert "pixels_done +=" in body_src or "_run_sequential" not in body_src, (
                "After MP fallback, pixels_done must be accumulated (+=), "
                "not overwritten (=)"
            )