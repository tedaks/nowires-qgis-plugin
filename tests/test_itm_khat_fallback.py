# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: ITM kHat near-zero fallback must use tolerance, not exact equality."""


def test_khat_equality_is_tolerance_based():
    """The kHat fallback branches must use abs(kHat) < tolerance, not == 0.0."""
    import os

    source_path = os.path.join(
        os.path.dirname(__file__), "..", "itm", "propagation.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    assert "if kHat_2 == 0.0:" not in source, (
        "kHat_2 exact float equality must be replaced with tolerance check"
    )
    assert "if kHat_1 == 0.0:" not in source, (
        "kHat_1 exact float equality must be replaced with tolerance check"
    )
    assert "abs(kHat" in source, (
        "kHat checks must use abs() tolerance pattern"
    )