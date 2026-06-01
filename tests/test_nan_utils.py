# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Tests for nan_utils — shared NaN interpolation helpers."""
import math
import numpy as np


def test_interpolate_nan_elevations_no_nan():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([1.0, 2.0, 3.0])
    np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


def test_interpolate_nan_elevations_middle_nan():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([1.0, float("nan"), 3.0])
    np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


def test_interpolate_nan_elevations_multiple_nans():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([1.0, float("nan"), float("nan"), 4.0, float("nan"), 6.0])
    np.testing.assert_array_equal(result, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])


def test_interpolate_nan_elevations_all_nan():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([float("nan"), float("nan")])
    assert all(math.isnan(float(x)) for x in result)


def test_interpolate_nan_elevations_leading_nan():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([float("nan"), 2.0, 3.0])
    assert float(result[1]) == 2.0
    assert float(result[2]) == 3.0
    assert float(result[0]) == 2.0  # nearest valid


def test_interpolate_nan_elevations_trailing_nan():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([1.0, 2.0, float("nan")])
    assert float(result[0]) == 1.0
    assert float(result[1]) == 2.0
    assert float(result[2]) == 2.0  # nearest valid


def test_interpolate_nan_elevations_single_value():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([5.0])
    assert len(result) == 1
    assert float(result[0]) == 5.0


def test_interpolate_nan_elevations_empty():
    from NoWires.nan_utils import interpolate_nan_elevations
    result = interpolate_nan_elevations([])
    assert len(result) == 0


def test_interpolate_nan_array_no_nan():
    from NoWires.nan_utils import interpolate_nan_array
    arr = np.array([1.0, 2.0, 3.0])
    result = interpolate_nan_array(arr)
    np.testing.assert_array_equal(result, arr)


def test_interpolate_nan_array_middle_nan():
    from NoWires.nan_utils import interpolate_nan_array
    arr = np.array([1.0, float("nan"), 3.0])
    result = interpolate_nan_array(arr)
    assert result[1] == 2.0


def test_interpolate_nan_array_all_nan():
    from NoWires.nan_utils import interpolate_nan_array
    arr = np.array([float("nan"), float("nan")])
    result = interpolate_nan_array(arr)
    assert np.all(np.isnan(result))


def test_interpolate_nan_array_preserves_dtype():
    from NoWires.nan_utils import interpolate_nan_array
    arr = np.array([1.0, 2.0, 3.0])
    result = interpolate_nan_array(arr)
    assert result.dtype == np.float64


def test_interpolate_nan_array_does_not_modify_original():
    from NoWires.nan_utils import interpolate_nan_array
    arr = np.array([1.0, float("nan"), 3.0])
    original = arr.copy()
    interpolate_nan_array(arr)
    np.testing.assert_array_equal(arr, original)


def test_interpolate_nan_array_all_nan_returns_copy():
    from NoWires.nan_utils import interpolate_nan_array
    arr = np.array([float("nan"), float("nan")])
    result = interpolate_nan_array(arr)
    result[0] = 42.0
    assert np.isnan(arr[0]), (
        "All-NaN branch must return a copy, not a reference to input")
