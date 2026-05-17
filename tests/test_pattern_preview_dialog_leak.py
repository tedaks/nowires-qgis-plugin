# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for antenna-preview dialog leak (v1.5.7 fix #10).

Source-level contract tests: _pattern_preview_dialog must be initialised
in __init__, closed-then-replaced in run_pattern_preview, and closed
in unload().
"""

import ast
import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "nowires.py"))


def _source():
    with open(_SOURCE_FILE) as f:
        return f.read()


def test_pattern_preview_dialog_initialised_in_init():
    """_pattern_preview_dialog must be initialised to None in __init__."""
    source = _source()
    tree = ast.parse(source)
    class_defs = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    plugin_cls = next(c for c in class_defs if c.name == "NoWiresPlugin")

    init_assigns = set()
    for node in ast.walk(plugin_cls):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Attribute):
                            init_assigns.add(target.attr)
    assert "_pattern_preview_dialog" in init_assigns, (
        "_pattern_preview_dialog must be initialised in NoWiresPlugin.__init__"
    )


def test_pattern_preview_dialog_closed_in_unload():
    """_pattern_preview_dialog must be closed in unload()."""
    source = _source()
    assert "_pattern_preview_dialog" in source
    # Also check unload() references it
    tree = ast.parse(source)
    class_defs = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    plugin_cls = next(c for c in class_defs if c.name == "NoWiresPlugin")

    found_close_in_unload = False
    for node in ast.walk(plugin_cls):
        if isinstance(node, ast.FunctionDef) and node.name == "unload":
            body_src = ast.unparse(node) if hasattr(ast, 'unparse') else ""
            if "_pattern_preview_dialog" in body_src or "_pattern_preview_dialog" in ast.dump(node):
                found_close_in_unload = True
    assert found_close_in_unload, (
        "unload() must close _pattern_preview_dialog"
    )


def test_run_pattern_preview_closes_existing():
    """run_pattern_preview must close any existing dialog before creating new one."""
    source = _source()
    lines = source.splitlines()
    found_close = False
    in_method = False
    for line in lines:
        if "def run_pattern_preview" in line:
            in_method = True
            continue
        if in_method and "def " in line and "run_pattern_preview" not in line:
            break
        if in_method and "_pattern_preview_dialog" in line and ".close()" in line:
            found_close = True
    assert found_close, (
        "run_pattern_preview must close any existing _pattern_preview_dialog "
        "before creating a new one"
    )