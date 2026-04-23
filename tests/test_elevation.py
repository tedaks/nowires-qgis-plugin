# -*- coding: utf-8 -*-
"""Unit tests for elevation.py — haversine, bearing, and ElevationGrid."""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from elevation import (
    haversine_m,
    bearing_deg,
    bearing_destination,
    sample_line_from_grid,
)


class TestHaversine:
    """Tests for haversine_m()."""

    def test_same_point(self):
        """Distance between identical points should be 0."""
        assert haversine_m(0, 0, 0, 0) == 0.0
        assert haversine_m(48.8566, 2.3522, 48.8566, 2.3522) == pytest.approx(0.0, abs=1.0)

    def test_known_distance(self):
        """Test known distances (approximate)."""
        # Paris to London: ~343 km
        d = haversine_m(48.8566, 2.3522, 51.5074, -0.1278)
        assert 330_000 < d < 360_000

    def test_equator_quarter_circle(self):
        """Quarter circle along the equator (~10,000 km)."""
        d = haversine_m(0, 0, 0, 90)
        assert 9_900_000 < d < 10_100_000

    def test_north_south(self):
        """Distance along a meridian."""
        # 1 degree of latitude ≈ 111 km
        d = haversine_m(0, 0, 1, 0)
        assert 110_000 < d < 112_000

    def test_symmetry(self):
        """haversine(a, b, c, d) should equal haversine(c, d, a, b)."""
        d1 = haversine_m(40.7128, -74.006, 51.5074, -0.1278)
        d2 = haversine_m(51.5074, -0.1278, 40.7128, -74.006)
        assert d1 == pytest.approx(d2, rel=1e-10)


class TestBearingDestination:
    """Tests for bearing_deg() and bearing_destination()."""

    def test_bearing_north(self):
        """Bearing from equator northward should be ~0 degrees."""
        b = bearing_deg(0, 0, 1, 0)
        assert b == pytest.approx(0.0, abs=0.5)

    def test_bearing_east(self):
        """Bearing from equator eastward should be ~90 degrees."""
        b = bearing_deg(0, 0, 0, 1)
        assert b == pytest.approx(90.0, abs=0.5)

    def test_bearing_south(self):
        """Bearing from equator southward should be ~180 degrees."""
        b = bearing_deg(0, 0, -1, 0)
        assert b == pytest.approx(180.0, abs=0.5)

    def test_bearing_west(self):
        """Bearing from equator westward should be ~270 degrees."""
        b = bearing_deg(0, 0, 0, -1)
        assert b == pytest.approx(270.0, abs=0.5)

    def test_destination_identity(self):
        """Zero distance should return the original point."""
        lat, lon = bearing_destination(48.8566, 2.3522, 45.0, 0)
        assert lat == pytest.approx(48.8566, abs=1e-10)
        assert lon == pytest.approx(2.3522, abs=1e-10)

    def test_destination_roundtrip(self):
        """Going 111 km north from equator should land near 1° latitude."""
        lat, lon = bearing_destination(0.0, 0.0, 0.0, 111_000)
        assert lat == pytest.approx(1.0, abs=0.01)
        assert lon == pytest.approx(0.0, abs=0.01)

    def test_destination_east_along_equator(self):
        """Going east along equator: 111km ≈ 1° longitude."""
        lat, lon = bearing_destination(0.0, 0.0, 90.0, 111_000)
        assert lat == pytest.approx(0.0, abs=0.01)
        assert lon == pytest.approx(1.0, abs=0.01)


class TestGridSamplingOrientation:
    """Tests for DEM north/south row orientation."""

    def test_sample_line_from_grid_keeps_north_at_top_row(self):
        grid = np.array(
            [
                [100.0, 110.0],
                [200.0, 210.0],
            ],
            dtype=np.float32,
        )
        meta = {
            "min_lat": 0.0,
            "max_lat": 1.0,
            "min_lon": 0.0,
            "max_lon": 1.0,
            "n_lat": 2,
            "n_lon": 2,
        }

        samples = sample_line_from_grid(
            grid,
            meta,
            lat1=1.0,
            lon1=0.0,
            lat2=0.0,
            lon2=0.0,
            n_pts=2,
        )

        assert samples[0] == pytest.approx(100.0)
        assert samples[1] == pytest.approx(200.0)


import pytest

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
