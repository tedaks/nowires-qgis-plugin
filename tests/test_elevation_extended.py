# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Additional behavioral tests for elevation.py — terrain_profile, context manager, grid_meta_dict."""

import numpy as np
import pytest

from elevation import ElevationGrid, bearing_deg


def _make_flat_grid(
    n_rows=10, n_cols=10, min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0, value=100.0
):
    grid = object.__new__(ElevationGrid)
    grid.data = np.full((n_rows, n_cols), value, dtype=np.float32)
    grid.n_rows = n_rows
    grid.n_cols = n_cols
    grid.min_lat = min_lat
    grid.max_lat = max_lat
    grid.min_lon = min_lon
    grid.max_lon = max_lon
    grid.d_lat = (max_lat - min_lat) / n_rows
    grid.d_lon = (max_lon - min_lon) / n_cols
    return grid


class TestElevationGridTerrainProfile:
    def test_terrain_profile_returns_distance_elevation_pairs(self):
        grid = _make_flat_grid(value=200.0)
        points = grid.terrain_profile(1.0, 0.0, 0.0, 0.0, step_m=10000.0)
        assert len(points) >= 2
        for d, elev in points:
            assert isinstance(d, float)
            assert isinstance(elev, float)

    def test_terrain_profile_starts_at_zero_distance(self):
        grid = _make_flat_grid(value=150.0)
        points = grid.terrain_profile(1.0, 0.0, 0.0, 0.0, step_m=10000.0)
        assert points[0][0] == pytest.approx(0.0)

    def test_terrain_profile_single_point_returns_two_points(self):
        grid = _make_flat_grid(n_rows=2, n_cols=2)
        points = grid.terrain_profile(0.5, 0.0, 0.5, 1.0, step_m=50000.0)
        assert len(points) >= 2

    def test_terrain_profile_flat_grid_constant_elevation(self):
        grid = _make_flat_grid(value=500.0)
        points = grid.terrain_profile(0.9, 0.0, 0.1, 1.0, step_m=50000.0)
        for _d, elev in points:
            assert elev == pytest.approx(500.0, abs=1.0)

    def test_terrain_profile_with_slope(self):
        data = np.zeros((10, 10), dtype=np.float32)
        for i in range(10):
            data[i, :] = float(i) * 100.0
        grid = object.__new__(ElevationGrid)
        grid.data = data
        grid.n_rows = 10
        grid.n_cols = 10
        grid.min_lat = 0.0
        grid.max_lat = 1.0
        grid.min_lon = 0.0
        grid.max_lon = 1.0
        grid.d_lat = 1.0 / 10
        grid.d_lon = 1.0 / 10

        points = grid.terrain_profile(1.0, 0.0, 0.0, 0.0, step_m=5000.0)
        first_elev = points[0][1]
        last_elev = points[-1][1]
        assert first_elev < last_elev


class TestElevationGridContextManager:
    def test_context_manager_calls_close(self):
        grid = _make_flat_grid(value=100.0)
        assert grid.data is not None
        with grid as eg:
            assert eg is grid
            assert eg.data is not None
        assert grid.data is None

    def test_close_releases_data(self):
        grid = _make_flat_grid(value=100.0)
        assert grid.data is not None
        grid.close()
        assert grid.data is None

    def test_close_idempotent(self):
        grid = _make_flat_grid()
        grid.close()
        grid.close()
        assert grid.data is None


class TestElevationGridGridMetaDict:
    def test_grid_meta_dict_returns_all_keys(self):
        grid = _make_flat_grid(n_rows=10, n_cols=20, min_lat=5.0, max_lat=6.0,
                                min_lon=100.0, max_lon=102.0)
        meta = grid.grid_meta_dict()
        assert "min_lat" in meta
        assert "max_lat" in meta
        assert "min_lon" in meta
        assert "max_lon" in meta
        assert "n_lat" in meta
        assert "n_lon" in meta

    def test_grid_meta_dict_values_are_correct(self):
        grid = _make_flat_grid(n_rows=10, n_cols=20, min_lat=5.0, max_lat=6.0,
                                min_lon=100.0, max_lon=102.0)
        meta = grid.grid_meta_dict()
        assert meta["min_lat"] == pytest.approx(5.0)
        assert meta["max_lat"] == pytest.approx(6.0)
        assert meta["min_lon"] == pytest.approx(100.0)
        assert meta["max_lon"] == pytest.approx(102.0)
        assert meta["n_lat"] == 10
        assert meta["n_lon"] == 20


class TestBearingEdgeCases:
    def test_bearing_identical_points(self):
        b = bearing_deg(10.0, 20.0, 10.0, 20.0)
        assert 0.0 <= b <= 360.0

    def test_bearing_north_pole_to_equator(self):
        b = bearing_deg(89.0, 0.0, 0.0, 0.0)
        assert b == pytest.approx(180.0, abs=1.0)

    def test_bearing_south_pole_to_equator(self):
        b = bearing_deg(-89.0, 0.0, 0.0, 0.0)
        assert b == pytest.approx(0.0, abs=1.0)

    def test_bearing_across_antimeridian(self):
        b = bearing_deg(0.0, 179.0, 0.0, -179.0)
        assert b == pytest.approx(90.0, abs=1.0)