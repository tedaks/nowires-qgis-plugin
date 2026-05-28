# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: K-factor parameter must be relabeled per ROADMAP."""

import os


def test_k_factor_not_called_earth_radius_factor():
    """The K-factor preset label must reflect it only affects Fresnel/LOS, not ITM."""
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "shared_params.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    assert "K_FACTOR_PRESET" in source
    assert "Fresnel Earth-radius factor" in source, (
        "K_FACTOR_PRESET label must be 'Fresnel Earth-radius factor' to clarify "
        "it affects only Fresnel/LOS display, not ITM propagation loss"
    )