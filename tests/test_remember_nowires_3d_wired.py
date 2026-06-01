# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verification that remember_nowires_3d_layers is wired from Coverage and P2P."""

import ast
import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)


def _source(relpath):
    path = os.path.normpath(os.path.join(_PLUGIN_DIR, relpath))
    with open(path) as f:
        return f.read()


def _all_call_names(source):
    """Return the set of bare function names called in the source."""
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_coverage_helpers_calls_remember():
    source = _source("algorithm/_coverage_helpers.py")
    assert "remember_nowires_3d_layers" in source


def test_p2p_compute_calls_remember():
    source = _source("p2p/compute.py")
    assert "remember_nowires_3d_layers" in source


def test_three_d_has_none_guard():
    source = _source("three_d.py")
    assert "def remember_nowires_3d_layers(" in source
    assert "if project is None:" in source
