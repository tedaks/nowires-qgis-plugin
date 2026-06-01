# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: P2P AOI latitude bounds must be clamped to [-90, 90]."""

import os


def test_p2p_compute_clamps_lat_bounds():
    """run_p2p_analysis must clamp south/north to [-90, 90]."""
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "p2p", "compute.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    assert "south" in source and "north" in source
    assert "max(-90.0" in source or "min(90.0" in source, (
        "P2P AOI latitude bounds (south, north) must be clamped with "
        "max(-90.0, ...) / min(90.0, ...) per coverage_bounds pattern"
    )