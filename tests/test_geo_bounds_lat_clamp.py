# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for coverage_bounds lat clamping and METERS_PER_DEGREE_LAT (v1.5.7 fix #11).

Before v1.5.7, coverage_bounds could return latitudes outside [-90, 90]
for near-pole TX positions with large radii, and used a local magic number
111320.0 instead of the shared METERS_PER_DEGREE_LAT constant.
"""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "geo_bounds.py"))


def test_coverage_bounds_clamps_south_to_minus_90():
    """A TX near the south pole must not return south < -90."""
    from NoWires.geo_bounds import coverage_bounds

    south, north, west, east = coverage_bounds(-89.0, 0.0, 300.0)
    assert south >= -90.0, f"south={south} exceeds -90"
    assert north <= 90.0, f"north={north} exceeds 90"


def test_coverage_bounds_clamps_north_to_90():
    """A TX near the north pole must not return north > 90."""
    from NoWires.geo_bounds import coverage_bounds

    south, north, west, east = coverage_bounds(89.0, 0.0, 300.0)
    assert south >= -90.0, f"south={south} is below -90"
    assert north <= 90.0, f"north={north} exceeds 90"


def test_coverage_bounds_uses_constant_not_magic_number():
    """geo_bounds must import METERS_PER_DEGREE_LAT, not hardcode 111320.0."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "111320.0" not in source, (
        "geo_bounds.py must not hardcode 111320.0; use METERS_PER_DEGREE_LAT from constants"
    )
    assert "METERS_PER_DEGREE_LAT" in source, (
        "geo_bounds.py must import and use METERS_PER_DEGREE_LAT"
    )


def test_coverage_bounds_equatorial():
    """Equatorial TX must produce sensible bounds."""
    from NoWires.geo_bounds import coverage_bounds

    south, north, west, east = coverage_bounds(0.0, 0.0, 50.0)
    assert -90.0 <= south <= 90.0
    assert -90.0 <= north <= 90.0