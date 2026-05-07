# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for p2p_compute: NaN handling and FSPL edge cases.

Tests import and verify the actual plugin modules (nan_utils, itm.propagation)
rather than reimplementing their logic inline.
"""

import math

import numpy as np
import pytest

from nan_utils import interpolate_nan_elevations, interpolate_nan_array
from itm.propagation import free_space_loss


class TestNaNInterpolation:
    """Verify that NaN elevation values are interpolated, not zeroed."""

    def test_interpolate_nan_elevations_replaces_nan_with_interpolated(self):
        elevations = [0.0, float("nan"), 100.0]
        result = interpolate_nan_elevations(elevations)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(50.0)
        assert result[2] == pytest.approx(100.0)

    def test_interpolate_nan_elevations_all_nan_returns_unchanged(self):
        elevations = [float("nan"), float("nan")]
        result = interpolate_nan_elevations(elevations)
        assert len(result) == 2
        assert all(math.isnan(v) for v in result)

    def test_interpolate_nan_elevations_no_nan_unchanged(self):
        elevations = [10.0, 20.0, 30.0]
        result = interpolate_nan_elevations(elevations)
        assert result == pytest.approx([10.0, 20.0, 30.0])

    def test_interpolate_nan_elevations_edge_nan_uses_nearest(self):
        elevations = [float("nan"), 20.0, 30.0]
        result = interpolate_nan_elevations(elevations)
        assert result[0] == pytest.approx(20.0)

    def test_interpolate_nan_elevations_trailing_nan_uses_nearest(self):
        elevations = [10.0, 20.0, float("nan")]
        result = interpolate_nan_elevations(elevations)
        assert result[2] == pytest.approx(20.0)

    def test_interpolate_nan_array_returns_ndarray(self):
        arr = np.array([1.0, np.nan, 3.0])
        result = interpolate_nan_array(arr)
        assert isinstance(result, np.ndarray)
        assert result[1] == pytest.approx(2.0)

    def test_interpolate_nan_array_preserves_valid(self):
        arr = np.array([10.0, 20.0, 30.0])
        result = interpolate_nan_array(arr)
        np.testing.assert_array_almost_equal(result, arr)


class TestFSPLFromModule:
    """Verify FSPL computation using the actual ITM propagation module."""

    def test_fspl_positive_distance_and_frequency(self):
        result = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        assert result > 0

    def test_fspl_zero_distance_raises_value_error(self):
        with pytest.raises(ValueError):
            free_space_loss(d__meter=0.0, f__mhz=900.0)

    def test_fspl_zero_frequency_raises_value_error(self):
        with pytest.raises(ValueError):
            free_space_loss(d__meter=1000.0, f__mhz=0.0)

    def test_fspl_uses_correct_constant(self):
        expected = 32.45 + 20.0 * math.log10(900.0) + 20.0 * math.log10(1.0)
        result = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_fspl_increases_with_distance(self):
        fspl_1km = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        fspl_10km = free_space_loss(d__meter=10000.0, f__mhz=900.0)
        assert fspl_10km > fspl_1km

    def test_fspl_increases_with_frequency(self):
        fspl_900 = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        fspl_2400 = free_space_loss(d__meter=1000.0, f__mhz=2400.0)
        assert fspl_2400 > fspl_900