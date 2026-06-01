# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Tests for _geo_utils pure-logic functions."""

import numpy as np

from _geo_utils import _interpolate_longitudes_shortest, sample_line_from_grid


class TestInterpolateLongitudesShortest:
    def test_simple_eastward_interpolation(self):
        lons = _interpolate_longitudes_shortest(0.0, 10.0, np.array([0.0, 0.5, 1.0]))
        np.testing.assert_allclose(lons, [0.0, 5.0, 10.0])

    def test_wraps_around_antimeridian_eastward(self):
        lons = _interpolate_longitudes_shortest(179.0, -179.0, np.array([0.0, 0.5, 1.0]))
        assert abs(lons[0] - 179.0) < 0.01
        assert abs(lons[2] - (-179.0)) < 0.01

    def test_wraps_around_antimeridian_westward(self):
        lons = _interpolate_longitudes_shortest(-179.0, 179.0, np.array([0.0, 0.5, 1.0]))
        assert lons[0] == -179.0
        assert lons[2] == 179.0
        assert abs(lons[1]) < 1.0 or abs(lons[1]) > 179.0

    def test_single_point(self):
        lons = _interpolate_longitudes_shortest(5.0, 5.0, np.array([0.0]))
        np.testing.assert_allclose(lons, [5.0])

    def test_backward_interpolation(self):
        lons = _interpolate_longitudes_shortest(10.0, 0.0, np.array([0.0, 0.5, 1.0]))
        np.testing.assert_allclose(lons, [10.0, 5.0, 0.0], atol=1e-10)


class TestSampleLineFromGrid:
    def _make_grid(self, data=None):
        if data is None:
            data = np.ones((10, 10), dtype=np.float32)
        return data, {
            "min_lat": 0.0, "max_lat": 10.0,
            "min_lon": 0.0, "max_lon": 10.0,
            "n_lat": data.shape[0], "n_lon": data.shape[1],
        }

    def test_diagonal_samples_on_grid(self):
        data, gm = self._make_grid(np.arange(100, dtype=np.float32).reshape(10, 10))
        result = sample_line_from_grid(data, gm, 0.5, 0.5, 9.5, 9.5, 10)
        assert len(result) == 10
        assert not np.all(np.isnan(result))

    def test_single_point_samples(self):
        data, gm = self._make_grid(np.full((10, 10), 5.0, dtype=np.float32))
        result = sample_line_from_grid(data, gm, 5.0, 5.0, 5.0, 5.0, 1)
        np.testing.assert_allclose(result, [5.0], atol=0.1)

    def test_out_of_bounds_returns_nan(self):
        data, gm = self._make_grid()
        result = sample_line_from_grid(data, gm, -10.0, -10.0, -9.0, -9.0, 3)
        assert all(np.isnan(result))

    def test_uniform_grid_returns_constant(self):
        data, gm = self._make_grid(np.full((10, 10), 7.5, dtype=np.float32))
        result = sample_line_from_grid(data, gm, 2.0, 2.0, 8.0, 8.0, 5)
        np.testing.assert_allclose(result, 7.5, atol=0.01)

    def test_gradient_grid_returns_expected_range(self):
        data = np.arange(100, dtype=np.float32).reshape(10, 10)
        _, gm = self._make_grid(data)
        result = sample_line_from_grid(data, gm, 5.0, 5.0, 5.0, 5.0, 1)
        assert not np.isnan(result[0])
        assert result[0] >= 0.0