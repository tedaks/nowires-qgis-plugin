# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for _write_p2p_output_layers returning fresnel_lines_path.

Before the fix, _write_p2p_output_layers omitted fresnel_lines_path from its
return tuple (only 3 values). The caller in p2p_compute.py reconstructed the
path from fresnel_poly_path using the same naming convention — a DRY violation
that would silently break if the naming convention ever changed.
"""
import ast
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def test_write_p2p_output_layers_returns_four_values():
    """_write_p2p_output_layers must return a 4-tuple including fresnel_lines_path."""
    source = (_ROOT / "p2p/outputs_internal.py").read_text()
    tree = ast.parse(source)
    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_write_p2p_output_layers":
            func = node
            break
    assert func is not None, "_write_p2p_output_layers function not found"
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
            assert len(node.value.elts) == 4, (
                "_write_p2p_output_layers must return 4 values "
                f"(profile_path, fresnel_poly_path, fresnel_lines_path, markers_path), "
                f"got {len(node.value.elts)}"
            )
            return
    raise AssertionError("No return tuple found in _write_p2p_output_layers")


def test_caller_unpacks_four_values():
    """p2p_compute.py must unpack all 4 return values, not reconstruct
    fresnel_lines_path from fresnel_poly_path."""
    source = (_ROOT / "p2p/compute.py").read_text()
    assert "fresnel_lines_path" in source, (
        "p2p_compute.py must unpack fresnel_lines_path from the return value"
    )
    lines = source.splitlines()
    for line in lines:
        if "_write_p2p_output_layers" in line and "=" in line and "import" not in line:
            assert "fresnel_lines_path" in line, (
                "Caller must unpack fresnel_lines_path from _write_p2p_output_layers"
            )
            parts = line.split("=", 1)[0].strip()
            names = [n.strip() for n in parts.strip("()").split(",")]
            assert len(names) == 4, (
                f"Caller must unpack 4 values, got {len(names)}: {names}"
            )
            break


def test_no_path_reconstruction_in_caller():
    """The caller must not reconstruct fresnel_lines_path from fresnel_poly_path,
    which would be a DRY violation."""
    source = (_ROOT / "p2p/compute.py").read_text()
    assert '_lines' not in [
        line for line in source.splitlines()
        if 'fresnel_poly' in line and '_lines' in line and '=' in line
        and 'fresnel_lines_path' not in line
    ] or "fresnel_lines_path" in source, (
        "fresnel_lines_path must come from _write_p2p_output_layers, "
        "not be reconstructed from fresnel_poly_path"
    )