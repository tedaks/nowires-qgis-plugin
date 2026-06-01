# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: south-up flip must produce contiguous array."""

import os


def test_elevation_south_up_flip_produces_contiguous():
    """The south-up data flip must produce a contiguous (C-order) array."""
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "elevation.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    assert "self.data[::-1]" in source
    assert "ascontiguousarray" in source or ".copy()" in source or (
        "numpy.ascontiguousarray" in source
    ), (
        "South-up data flip must call np.ascontiguousarray() or .copy() "
        "to ensure contiguous memory for bilinear sampling hot path"
    )