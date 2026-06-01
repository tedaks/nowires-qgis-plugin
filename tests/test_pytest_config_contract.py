# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for root-level pytest configuration discovery."""

from pathlib import Path


def test_benchmark_marker_registered_at_repo_root():
    root_pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    assert root_pyproject.exists()
    text = root_pyproject.read_text(encoding="utf-8")
    assert "benchmark:" in text

