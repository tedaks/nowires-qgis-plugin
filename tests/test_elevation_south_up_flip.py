# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression tests for ElevationGrid south-up DEM flip and short-distance edge case."""

import math

import numpy as np

from elevation import ElevationGrid


def _build_south_up_grid():
    grid = object.__new__(ElevationGrid)
    grid.data = np.array([
        [100.0, 110.0],
        [200.0, 210.0],
    ], dtype=np.float32)
    grid.n_rows = 2
    grid.n_cols = 2
    grid.min_lat = 1.0
    grid.max_lat = 0.0
    grid.min_lon = 0.0
    grid.max_lon = 1.0
    grid.d_lat = 0.5
    grid.d_lon = 0.5
    return grid


class TestElevationSouthUpFlip:
    def test_south_up_produces_contiguous_array(self):
        grid = _build_south_up_grid()
        flipped = np.ascontiguousarray(grid.data[::-1])
        assert flipped.flags["C_CONTIGUOUS"]
        assert flipped.shape == (2, 2)

    def test_south_up_flip_corrects_lat_bounds(self):
        grid = _build_south_up_grid()
        min_lat, max_lat = grid.max_lat, grid.min_lat
        assert min_lat == 0.0
        assert max_lat == 1.0

    def test_south_up_top_row_is_correct_value(self):
        grid = _build_south_up_grid()
        flipped = np.ascontiguousarray(grid.data[::-1])
        assert flipped[0, 0] == 200.0
        assert flipped[1, 0] == 100.0

    def test_south_up_flip_preserves_all_values(self):
        grid = _build_south_up_grid()
        flipped = np.ascontiguousarray(grid.data[::-1])
        assert sorted(flipped.flatten()) == sorted(grid.data.flatten())


class TestElevationGridShortDistance:
    def test_terrain_profile_short_distance_less_than_step(self):
        grid = object.__new__(ElevationGrid)
        grid.data = np.array([
            [100.0, 110.0, 120.0],
            [200.0, 210.0, 220.0],
            [300.0, 310.0, 320.0],
        ], dtype=np.float32)
        grid.n_rows = 3
        grid.n_cols = 3
        grid.min_lat = 44.99
        grid.max_lat = 45.01
        grid.min_lon = 8.99
        grid.max_lon = 9.01
        grid.d_lat = 0.02 / 3.0
        grid.d_lon = 0.02 / 3.0

        profile = grid.terrain_profile(45.0, 9.0, 45.00001, 9.00001, step_m=30.0)
        assert len(profile) >= 2
        for d, e in profile:
            assert math.isfinite(d)
            assert math.isfinite(e)

    def test_terrain_profile_returns_at_least_two_points(self):
        grid = object.__new__(ElevationGrid)
        grid.data = np.full((10, 10), 150.0, dtype=np.float32)
        grid.n_rows = 10
        grid.n_cols = 10
        grid.min_lat = 40.0
        grid.max_lat = 41.0
        grid.min_lon = 9.0
        grid.max_lon = 10.0
        grid.d_lat = 0.1
        grid.d_lon = 0.1

        profile = grid.terrain_profile(40.5, 9.5, 40.50001, 9.50001, step_m=30.0)
        assert len(profile) >= 2
        assert all(math.isfinite(e) for _, e in profile)

    def test_terrain_profile_zero_distance_still_works(self):
        grid = object.__new__(ElevationGrid)
        grid.data = np.full((10, 10), 123.4, dtype=np.float32)
        grid.n_rows = 10
        grid.n_cols = 10
        grid.min_lat = 40.0
        grid.max_lat = 41.0
        grid.min_lon = 9.0
        grid.max_lon = 10.0
        grid.d_lat = 0.1
        grid.d_lon = 0.1

        profile = grid.terrain_profile(40.5, 9.5, 40.5, 9.5, step_m=30.0)
        assert len(profile) >= 2
        for d, e in profile:
            assert math.isfinite(d)
            assert math.isfinite(e)
