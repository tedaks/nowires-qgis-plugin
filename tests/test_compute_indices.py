# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the shared _compute_indices helper in _bilinear.py."""

import numpy as np

from NoWires._bilinear import _compute_indices


class TestComputeIndices:
    def test_scalar_at_center_returns_expected_indices(self):
        gm = {"n_lat": 10, "n_lon": 10, "min_lat": 10.0, "max_lat": 20.0, "min_lon": 100.0, "max_lon": 110.0}
        lats = np.array([15.0], dtype=np.float64)
        lons = np.array([105.0], dtype=np.float64)
        y0, x0, y1, x1, ty, tx, oob = _compute_indices(gm, lats, lons)
        assert not oob[0]
        assert 0 <= int(y0[0]) < 9
        assert 0 <= int(x0[0]) < 9
        assert 0.0 <= float(ty[0]) <= 1.0
        assert 0.0 <= float(tx[0]) <= 1.0

    def test_out_of_bounds_detected(self):
        gm = {"n_lat": 5, "n_lon": 5, "min_lat": 0.0, "max_lat": 5.0, "min_lon": 0.0, "max_lon": 5.0}
        lats = np.array([-1.0], dtype=np.float64)
        lons = np.array([2.5], dtype=np.float64)
        y0, x0, y1, x1, ty, tx, oob = _compute_indices(gm, lats, lons)
        assert oob[0]

    def test_vector_computes_all_indices(self):
        gm = {"n_lat": 4, "n_lon": 4, "min_lat": 0.0, "max_lat": 4.0, "min_lon": 0.0, "max_lon": 4.0}
        lats = np.array([0.5, 3.5], dtype=np.float64)
        lons = np.array([0.5, 3.5], dtype=np.float64)
        y0, x0, y1, x1, ty, tx, oob = _compute_indices(gm, lats, lons)
        assert y0.shape == (2,)
        assert x0.shape == (2,)
        assert not oob.any()

    def test_boundary_point_not_oob(self):
        gm = {"n_lat": 10, "n_lon": 10, "min_lat": 10.0, "max_lat": 20.0, "min_lon": 100.0, "max_lon": 110.0}
        lats = np.array([10.0], dtype=np.float64)
        lons = np.array([100.0], dtype=np.float64)
        y0, x0, y1, x1, ty, tx, oob = _compute_indices(gm, lats, lons)
        assert not oob[0]

    def test_grid_2d_shape(self):
        gm = {"n_lat": 5, "n_lon": 3, "min_lat": 0.0, "max_lat": 5.0, "min_lon": 0.0, "max_lon": 3.0}
        lats = np.broadcast_to(np.array([1.0, 4.0], dtype=np.float64)[:, np.newaxis], (2, 2))
        lons = np.broadcast_to(np.array([0.5, 2.5], dtype=np.float64)[np.newaxis, :], (2, 2))
        y0, x0, y1, x1, ty, tx, oob = _compute_indices(gm, lats, lons)
        assert y0.shape == (2, 2)
        assert x0.shape == (2, 2)
        assert oob.shape == (2, 2)
