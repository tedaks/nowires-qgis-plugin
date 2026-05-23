# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended unit tests for elevation.py — sample_grid, terrain_profile edge cases."""

import math

import numpy as np
import pytest

from NoWires.elevation import ElevationGrid


def _make_mini_grid(data=None):
    """Build a 5x5 ElevationGrid without GDAL."""
    if data is None:
        data = np.array([
            [10.0, 20.0, 30.0, 20.0, 10.0],
            [20.0, 30.0, 40.0, 30.0, 20.0],
            [30.0, 40.0, 50.0, 40.0, 30.0],
            [20.0, 30.0, 40.0, 30.0, 20.0],
            [10.0, 20.0, 30.0, 20.0, 10.0],
        ], dtype=np.float32)
    grid = object.__new__(ElevationGrid)
    grid.data = data
    grid.n_rows, grid.n_cols = data.shape
    grid.min_lat = 0.0
    grid.max_lat = 5.0
    grid.min_lon = 0.0
    grid.max_lon = 5.0
    grid.d_lat = 1.0
    grid.d_lon = 1.0
    return grid


class TestElevationGridSampleGrid:
    def test_basic_2d_sampling(self):
        grid = _make_mini_grid()
        lats = [1.0, 2.0, 3.0]
        lons = [1.0, 2.0, 3.0]
        result = grid.sample_grid(lats, lons)
        assert result.shape == (3, 3)
        assert result.dtype in (np.float32, np.float64)

    def test_center_pixel_value(self):
        grid = _make_mini_grid()
        lats = [2.5]
        lons = [2.5]
        result = grid.sample_grid(lats, lons)
        assert result.shape == (1, 1)
        assert result[0, 0] == pytest.approx(50.0)

    def test_single_row_multiple_cols(self):
        grid = _make_mini_grid()
        lats = [2.5]
        lons = [0.5, 2.5, 4.5]
        result = grid.sample_grid(lats, lons)
        assert result.shape == (1, 3)

    def test_single_col_multiple_rows(self):
        grid = _make_mini_grid()
        lats = [0.5, 2.5, 4.5]
        lons = [2.5]
        result = grid.sample_grid(lats, lons)
        assert result.shape == (3, 1)

    def test_out_of_bounds_returns_nan(self):
        grid = _make_mini_grid()
        lats = [10.0]
        lons = [10.0]
        result = grid.sample_grid(lats, lons)
        assert math.isnan(result[0, 0])

    def test_partial_out_of_bounds(self):
        grid = _make_mini_grid()
        lats = [2.5, 10.0]
        lons = [2.5]
        result = grid.sample_grid(lats, lons)
        assert not math.isnan(result[0, 0])
        assert math.isnan(result[1, 0])


class TestElevationGridSample:
    def test_sample_at_all_corners(self):
        grid = _make_mini_grid()
        assert not math.isnan(grid.sample(0.5, 0.5))
        assert not math.isnan(grid.sample(0.5, 4.5))
        assert not math.isnan(grid.sample(4.5, 0.5))
        assert not math.isnan(grid.sample(4.5, 4.5))

    def test_sample_near_edge(self):
        grid = _make_mini_grid()
        val = grid.sample(0.001, 2.5)
        assert not math.isnan(val)

    def test_sample_bilinear_interpolation(self):
        data = np.array([[0.0, 10.0], [10.0, 20.0]], dtype=np.float32)
        grid = object.__new__(ElevationGrid)
        grid.data = data
        grid.n_rows, grid.n_cols = 2, 2
        grid.min_lat = 0.0
        grid.max_lat = 2.0
        grid.min_lon = 0.0
        grid.max_lon = 2.0
        grid.d_lat = 1.0
        grid.d_lon = 1.0
        val = grid.sample(1.5, 0.5)
        assert val == pytest.approx(0.0, abs=0.1)
        val = grid.sample(1.0, 1.0)
        assert 5.0 < val < 25.0


class TestTerrainProfile:
    def test_short_distance_uses_minimum_step(self):
        data = np.full((5, 5), 100.0, dtype=np.float32)
        grid = _make_mini_grid(data=data)
        lat1, lon1 = 2.5, 2.5
        lat2, lon2 = 2.50001, 2.50001
        profile = grid.terrain_profile(lat1, lon1, lat2, lon2, step_m=30.0)
        assert len(profile) >= 2
        for d, e in profile:
            assert math.isfinite(d)
            assert math.isfinite(e)

    def test_profile_over_long_distance(self):
        data = np.full((5, 5), 100.0, dtype=np.float32)
        grid = _make_mini_grid(data=data)
        lat1, lat2 = 1.5, 3.5
        lon1, lon2 = 1.5, 3.5
        profile = grid.terrain_profile(lat1, lon1, lat2, lon2, step_m=50000.0)
        assert len(profile) >= 2
        assert profile[0][0] == 0.0

    def test_profile_distances_are_monotonic(self):
        data = np.full((5, 5), 100.0, dtype=np.float32)
        grid = _make_mini_grid(data=data)
        profile = grid.terrain_profile(1.5, 1.5, 3.5, 1.5, step_m=20000.0)
        distances = [d for d, _ in profile]
        for i in range(len(distances) - 1):
            assert distances[i] <= distances[i + 1]

    def test_profile_same_point(self):
        data = np.full((5, 5), 100.0, dtype=np.float32)
        grid = _make_mini_grid(data=data)
        profile = grid.terrain_profile(2.5, 2.5, 2.5, 2.5, step_m=30.0)
        assert len(profile) >= 2


class TestGridMetaDict:
    def test_meta_dict_has_expected_keys(self):
        grid = _make_mini_grid()
        meta = grid.grid_meta_dict()
        assert "min_lat" in meta
        assert "max_lat" in meta
        assert "min_lon" in meta
        assert "max_lon" in meta
        assert "n_lat" in meta
        assert "n_lon" in meta
        assert meta["n_lat"] == 5
        assert meta["n_lon"] == 5


class TestElevationGridClose:
    def test_close_sets_data_to_none(self):
        grid = _make_mini_grid()
        assert grid.data is not None
        grid.close()
        assert grid.data is None

    def test_context_manager_closes(self):
        grid = _make_mini_grid()
        with grid:
            assert grid.data is not None
        assert grid.data is None

    def test_close_idempotent(self):
        grid = _make_mini_grid()
        grid.close()
        grid.close()
        assert grid.data is None


class TestSampleLine:
    def test_sample_line_nan_at_out_of_bounds(self):
        data = np.full((5, 5), 100.0, dtype=np.float32)
        grid = _make_mini_grid(data=data)
        result = grid.sample_line(2.5, 2.5, 10.0, 10.0, 5)
        assert len(result) == 5
        assert not math.isnan(result[0])
        assert math.isnan(result[-1])

    def test_sample_line_all_in_bounds(self):
        data = np.full((5, 5), 100.0, dtype=np.float32)
        grid = _make_mini_grid(data=data)
        result = grid.sample_line(2.5, 2.5, 2.5, 2.5, 3)
        assert len(result) == 3
        assert not np.isnan(result).any()
