# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Unit tests for geo_bounds.py — longitude normalization, intervals, and coverage bounds."""

import math

import pytest

from geo_bounds import (
    coverage_bounds,
    normalize_longitude,
    longitude_intervals,
    shortest_longitude_bounds,
    shortest_longitude_bounds_for,
)


class TestNormalizeLongitude:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (0.0, 0.0),
            (45.0, 45.0),
            (179.0, 179.0),
            (-45.0, -45.0),
            (-179.0, -179.0),
            (180.0, -180.0),
            (-180.0, -180.0),
            (360.0, 0.0),
            (-360.0, 0.0),
            (540.0, -180.0),  # 540 normalizes to -180
            (-540.0, -180.0),  # -540 + 180 = -360 % 360 = 0, 0 - 180 = -180
            (720.0, 0.0),
            (-720.0, 0.0),
            (270.0, -90.0),
            (-270.0, 90.0),
            (0.5, 0.5),
            (359.9, -0.1),
        ],
    )
    def test_normalization(self, value, expected):
        assert normalize_longitude(value) == pytest.approx(expected)

    def test_boundary_invariant(self):
        assert normalize_longitude(180.0) < 180.0
        assert normalize_longitude(-180.0) >= -180.0


class TestLongitudeIntervals:
    @pytest.mark.parametrize(
        "west, east, expected",
        [
            (0.0, 90.0, [(0.0, 90.0)]),
            (-45.0, 45.0, [(-45.0, 45.0)]),
            (170.0, -170.0, [(170.0, 180.0), (-180.0, -170.0)]),
            (90.0, 0.0, [(90.0, 180.0), (-180.0, 0.0)]),
        ],
    )
    def test_intervals(self, west, east, expected):
        result = longitude_intervals(west, east)
        assert len(result) == len(expected)
        for got, exp in zip(result, expected):
            assert got == pytest.approx(exp)

    def test_same_west_east(self):
        result = longitude_intervals(50.0, 50.0)
        assert result == [(50.0, 50.0)]

    def test_wrapping_normalizes_inputs(self):
        # 370 -> 10, -350 -> 10; same value so no wrapping
        result = longitude_intervals(370.0, -350.0)
        assert result == [(10.0, 10.0)]


class TestCoverageBounds:
    def test_equatorial_location(self):
        south, north, west, east = coverage_bounds(0.0, 0.0, 100.0)
        deg_per_100km_lat = 100_000 / 111320.0
        deg_per_100km_lon = 100_000 / (111320.0 * 1.0)
        assert south == pytest.approx(-deg_per_100km_lat, abs=1e-10)
        assert north == pytest.approx(deg_per_100km_lat, abs=1e-10)
        assert west == pytest.approx(-deg_per_100km_lon, abs=1e-10)
        assert east == pytest.approx(deg_per_100km_lon, abs=1e-10)

    def test_high_latitude_cos_correction(self):
        cos_60 = math.cos(math.radians(60.0))
        _, _, west, east = coverage_bounds(60.0, 30.0, 100.0)
        half_lon_deg = 100_000 / (111320.0 * cos_60)
        assert east == pytest.approx(30.0 + half_lon_deg)
        assert west == pytest.approx(30.0 - half_lon_deg)

    def test_zero_radius(self):
        south, north, west, east = coverage_bounds(40.0, -80.0, 0.0)
        assert south == pytest.approx(40.0)
        assert north == pytest.approx(40.0)
        assert west == pytest.approx(-80.0)
        assert east == pytest.approx(-80.0)

    def test_zero_padding(self):
        s1, n1, w1, e1 = coverage_bounds(10.0, 20.0, 50.0, padding_deg=0.0)
        s2, n2, w2, e2 = coverage_bounds(10.0, 20.0, 50.0, padding_deg=0.5)
        assert s2 < s1
        assert n2 > n1
        assert w2 < w1
        assert e2 > e1


class TestShortestLongitudeBounds:
    def test_nearby_longitudes(self):
        west, east = shortest_longitude_bounds(10.0, 20.0)
        assert west == pytest.approx(10.0)
        assert east == pytest.approx(20.0)

    def test_across_antimeridian(self):
        west, east = shortest_longitude_bounds(170.0, -170.0)
        assert west == pytest.approx(170.0)
        assert east == pytest.approx(-170.0)

    def test_same_longitude(self):
        west, east = shortest_longitude_bounds(45.0, 45.0)
        assert west == pytest.approx(45.0)
        assert east == pytest.approx(45.0)

    def test_with_padding(self):
        west, east = shortest_longitude_bounds(10.0, 20.0, padding_deg=1.0)
        assert west == pytest.approx(9.0)
        assert east == pytest.approx(21.0)


class TestShortestLongitudeBoundsFor:
    def test_single_point(self):
        west, east = shortest_longitude_bounds_for([45.0])
        assert west == pytest.approx(45.0)
        assert east == pytest.approx(45.0)

    def test_multiple_points_same_hemisphere(self):
        west, east = shortest_longitude_bounds_for([10.0, 20.0, 30.0])
        assert west == pytest.approx(10.0)
        assert east == pytest.approx(30.0)

    def test_points_spanning_antimeridian(self):
        west, east = shortest_longitude_bounds_for([170.0, -170.0, 175.0])
        assert west == pytest.approx(170.0)
        assert east == pytest.approx(-170.0)

    def test_empty_list(self):
        west, east = shortest_longitude_bounds_for([])
        assert west == pytest.approx(-180.0)
        assert east == pytest.approx(180.0)

    def test_with_padding(self):
        west, east = shortest_longitude_bounds_for([10.0, 20.0], padding_deg=2.0)
        assert west == pytest.approx(8.0)
        assert east == pytest.approx(22.0)

    def test_all_same_longitude(self):
        west, east = shortest_longitude_bounds_for([50.0, 50.0, 50.0])
        assert west == pytest.approx(50.0)
        assert east == pytest.approx(50.0)

    def test_padding_covers_globe(self):
        west, east = shortest_longitude_bounds_for([10.0, 20.0], padding_deg=180.0)
        assert west == pytest.approx(-180.0)
        assert east == pytest.approx(180.0)

    def test_farthest_apart_pair(self):
        # 0, 90, 180 -> largest gap is 180->360 (180 deg), covers 0->180
        west, east = shortest_longitude_bounds_for([0.0, 90.0, 180.0])
        assert west == pytest.approx(0.0)
        assert east == pytest.approx(-180.0)