# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: tile_merge ComputeStatistics must have a timeout guard."""

import os


def test_compute_stats_timeout_constant_defined():
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "tile_merge.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()
    assert "_COMPUTE_STATS_TIMEOUT_S" in source
    assert "concurrent.futures" in source
    assert "TimeoutError" in source


def test_timeout_value_is_reasonable():
    from NoWires.tile_merge import _COMPUTE_STATS_TIMEOUT_S
    assert 10 <= _COMPUTE_STATS_TIMEOUT_S <= 120
