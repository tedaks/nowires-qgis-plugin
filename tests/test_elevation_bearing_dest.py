# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression tests for bearing_destination edge cases and asin clamping."""

import math

import pytest

from elevation import bearing_destination


class TestBearingDestinationEdgeCases:
    """Edge cases for bearing_destination math.asin clamping."""

    def test_near_antipodal_north_stays_finite(self):
        """Near-antipodal bearing north should not produce NaN."""
        lat, lon = bearing_destination(
            89.0, 0.0, 0.0, 20_037_000,  # half circumference ~20,037 km
        )
        assert math.isfinite(lat)
        assert math.isfinite(lon)
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lon <= 180.0

    def test_exactly_antipodal_latitude_clamped(self):
        """Exact antipodal distance produces latitude near -origin."""
        origin_lat = 45.0
        lat, lon = bearing_destination(
            origin_lat, 0.0, 0.0, 20_037_508,  # half circumference
        )
        assert math.isfinite(lat)
        assert -90.0 <= lat <= 90.0

    def test_extreme_distance_clamped_to_asin_domain(self):
        """Distance exceeding half circumference triggers asin clamp."""
        lat, lon = bearing_destination(
            0.0, 0.0, 90.0, 40_000_000,  # exceeds Earth circumference
        )
        assert math.isfinite(lat)
        assert math.isfinite(lon)
        assert -90.0 <= lat <= 90.0

    def test_zero_distance_preserves_identity(self):
        """Zero distance returns the origin point."""
        lat, lon = bearing_destination(48.8566, 2.3522, 45.0, 0.0)
        assert lat == pytest.approx(48.8566, abs=1e-10)
        assert lon == pytest.approx(2.3522, abs=1e-10)

    def test_longitude_normalized_negative_wrap(self):
        """Westward motion from -179 wraps longitude correctly."""
        _lat, lon = bearing_destination(0.0, -179.0, 270.0, 300_000)
        assert -180.0 <= lon <= 180.0

    def test_longitude_normalized_east_wrap_from_positive(self):
        """Eastward motion from +179 wraps longitude correctly."""
        _lat, lon = bearing_destination(0.0, 179.0, 90.0, 300_000)
        assert -180.0 <= lon <= 180.0

    def test_south_bearing_quarter_circumference(self):
        """Quarter circumference south produces valid latitudes."""
        lat, lon = bearing_destination(
            0.0, 0.0, 180.0, 10_018_754,
        )
        assert math.isfinite(lat)
        assert -90.0 <= lat <= 90.0

    def test_float_overflow_distance_still_produces_finite(self):
        """Very large distance (1e9 m) should still produce finite results."""
        lat, lon = bearing_destination(0.0, 0.0, 180.0, 1e9)
        assert math.isfinite(lat)
        assert math.isfinite(lon)
