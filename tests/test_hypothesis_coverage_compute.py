# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Property-based tests for coverage_compute.py using hypothesis."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from NoWires.constants import COVERAGE_NODATA
from NoWires.raster_io import grid_to_raster_array


class TestGridToRasterArrayProperties:
    @given(
        rows=st.integers(min_value=1, max_value=20),
        cols=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=30)
    def test_output_shape_matches_input(self, rows, cols):
        grid = np.random.rand(rows, cols).astype(np.float32)
        result = grid_to_raster_array(grid)
        assert result.shape == (rows, cols)

    @given(
        rows=st.integers(min_value=1, max_value=10),
        cols=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=20)
    def test_nan_replaced_by_nodata(self, rows, cols):
        grid = np.full((rows, cols), float("nan"), dtype=np.float32)
        result = grid_to_raster_array(grid)
        assert np.all(result == COVERAGE_NODATA)

    @given(val=st.floats(min_value=-200.0, max_value=50.0, allow_nan=False,
                          allow_infinity=False, width=32))
    @settings(max_examples=30)
    def test_valid_values_preserved(self, val):
        grid = np.full((2, 2), val, dtype=np.float32)
        result = grid_to_raster_array(grid)
        assert np.all(result == pytest.approx(val, abs=0.1))

    @given(
        rows=st.integers(min_value=2, max_value=10),
        cols=st.integers(min_value=2, max_value=10),
    )
    @settings(max_examples=20)
    def test_raster_is_vertically_flipped(self, rows, cols):
        grid = np.arange(rows * cols, dtype=np.float32).reshape(rows, cols)
        result = grid_to_raster_array(grid)
        np.testing.assert_array_equal(result[0, :], grid[-1, :])