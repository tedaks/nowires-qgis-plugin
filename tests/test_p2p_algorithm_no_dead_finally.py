# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Contract test: algorithm/p2p.py must not wrap run_p2p_analysis in dead try/finally."""

import ast
import os


def _p2p_algorithm_source():
    path = os.path.join(os.path.dirname(__file__), "..", "algorithm", "p2p.py")
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_p2p_algorithm_calls_run_p2p_analysis_directly():
    """The call must remain, but it must not be wrapped in try/finally inside processAlgorithm."""
    source = _p2p_algorithm_source()
    assert "run_p2p_analysis(p2p_params)" in source


def test_p2p_algorithm_has_no_pass_only_finally():
    """No try-finally block where the finally body is just a single `pass` may remain.

    AST-level check so it doesn't depend on comment placement.
    """
    tree = ast.parse(_p2p_algorithm_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and node.finalbody:
            stmts = node.finalbody
            if len(stmts) == 1 and isinstance(stmts[0], ast.Pass):
                raise AssertionError(
                    "Dead try-finally with `finally: pass` remains at line "
                    f"{node.lineno}"
                )
