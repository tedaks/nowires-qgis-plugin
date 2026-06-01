# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for clutter grid resource leak on early exception.

Before the fix, clutter_grid.close() was in a finally block that only
covered the output-writing section. If DEM download, elevation, or ITM
prediction failed before reaching that try block, the clutter grid was
never closed — a significant leak in long-running QGIS sessions with
large land-cover rasters.
"""
import ast
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def test_try_covers_clutter_grid_acquisition():
    """The try block must start no later than 3 lines after owns_clutter_grid
    assignment so that exceptions during DEM download, elevation processing,
    or ITM prediction trigger the finally clause that closes the clutter grid."""
    source = (_ROOT / "p2p/compute.py").read_text()

    lines = source.splitlines()
    owns_line = None
    for i, line in enumerate(lines):
        if "owns_clutter_grid" in line and "clutter_grid is not None" in line:
            owns_line = i + 1
            break
    assert owns_line is not None, "owns_clutter_grid assignment not found"

    tree = ast.parse(source)
    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_p2p_analysis":
            func = node
            break
    assert func is not None, "run_p2p_analysis not found"

    try_line = None
    for node in func.body:
        if isinstance(node, ast.Try):
            try_line = node.lineno
            break
    assert try_line is not None, "try statement not found in run_p2p_analysis"

    assert try_line <= owns_line + 3, (
        f"try block must start within 3 lines of owns_clutter_grid (owns={owns_line}, "
        f"try={try_line}). Currently the gap is too large — exceptions between "
        f"clutter-grid acquisition and the try block would leak the grid."
    )