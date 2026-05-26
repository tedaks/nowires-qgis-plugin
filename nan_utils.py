# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Shared NaN interpolation helpers for NoWires.

Replaces duplicated _interpolate_nan_elevations in coverage_pool.py
and p2p_compute.py with a single consolidated implementation.
"""

import numpy as np


def interpolate_nan_elevations(elevations):
    """Replace NaN elevation values with linearly interpolated neighbours.

    Falls back to the nearest valid value at the edges. Returns the array
    unchanged if all values are NaN (caller checks np.all(isnan) separately).

    Args:
        elevations: Array-like of elevation values (may contain NaN).

    Returns:
        numpy.ndarray: Interpolated elevation values with NaN replaced.
    """
    arr = np.asarray(elevations, dtype=np.float64)
    nan_mask = np.isnan(arr)
    if not nan_mask.any() or not (~nan_mask).any():
        return arr.copy()
    valid_idx = np.where(~nan_mask)[0]
    arr = arr.copy()
    arr[nan_mask] = np.interp(np.where(nan_mask)[0], valid_idx, arr[valid_idx])
    return arr


def interpolate_nan_array(arr):
    """Replace NaN values with linearly interpolated neighbours (numpy return).

    Same logic as interpolate_nan_elevations but returns a numpy array
    instead of a list, for use in the sequential coverage path.

    Args:
        arr: numpy array that may contain NaN values.

    Returns:
        numpy.ndarray: Copy with NaN values replaced by interpolation.
    """
    arr = np.asarray(arr, dtype=np.float64)
    nan_mask = np.isnan(arr)
    if not nan_mask.any():
        return arr.copy()
    valid_mask = ~nan_mask
    if not valid_mask.any():
        return arr.copy()
    valid_indices = np.where(valid_mask)[0]
    result = arr.copy()
    nan_indices = np.where(nan_mask)[0]
    result[nan_indices] = np.interp(nan_indices, valid_indices, arr[valid_indices])
    return result
