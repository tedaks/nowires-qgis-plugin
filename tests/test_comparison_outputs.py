# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for comparison_outputs.compute_delta_summary.

SKIPPED when real QGIS is available because they mock QGIS shader types.
"""

import os
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest

_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))

pytestmark = pytest.mark.skipif(
    _HAS_REAL_QGIS,
    reason="Comparison output tests mock QGIS shader types incompatible with real QGIS",
)

qgis = types.ModuleType("qgis")
qgis_core = types.ModuleType("qgis.core")
qgis_core.QgsColorRampShader = MagicMock
qgis_core.QgsRasterShader = MagicMock
qgis_core.QgsSingleBandPseudoColorRenderer = MagicMock
sys.modules.setdefault("qgis", qgis)
sys.modules.setdefault("qgis.core", qgis_core)

from NoWires.comparison.outputs import compute_delta_summary


class TestComputeDeltaSummary:
    def test_basic_delta_improved_degraded_unchanged(self):
        a = np.array([[6.0, 12.0, 14.0]])
        b = np.array([[10.0, 12.0, 16.0]])
        ds = compute_delta_summary(a, b, threshold_db=3.0)
        assert ds["valid_count"] == 3
        assert ds["total_count"] == 3
        assert ds["improved"] == 1
        assert ds["degraded"] == 0
        assert ds["unchanged"] == 2

    def test_all_nan_a_returns_zero_valid(self):
        a = np.full((2, 3), np.nan)
        b = np.ones((2, 3))
        ds = compute_delta_summary(a, b, threshold_db=5.0)
        assert ds["valid_count"] == 0
        assert ds["total_count"] == 0
        assert ds["improved"] == 0
        assert ds["degraded"] == 0
        assert ds["unchanged"] == 0
        assert ds["min_delta"] == 0.0
        assert ds["max_delta"] == 0.0
        assert ds["mean_delta"] == 0.0

    def test_all_nan_b_returns_zero_valid(self):
        a = np.ones((2, 3))
        b = np.full((2, 3), np.nan)
        ds = compute_delta_summary(a, b, threshold_db=5.0)
        assert ds["valid_count"] == 0
        assert ds["total_count"] == 0

    def test_partial_nan_only_valid_pixels_counted(self):
        a = np.array([[8.0, np.nan, 14.0]])
        b = np.array([[10.0, 12.0, np.nan]])
        ds = compute_delta_summary(a, b, threshold_db=1.0)
        assert ds["valid_count"] == 1
        assert ds["total_count"] == 1
        assert ds["improved"] == 1

    def test_threshold_zero_no_change(self):
        a = np.array([[5.0, 5.0]])
        b = np.array([[5.0, 5.0]])
        ds = compute_delta_summary(a, b, threshold_db=0.0)
        assert ds["improved"] == 0
        assert ds["degraded"] == 0
        assert ds["unchanged"] == 2

    def test_delta_values_are_correct(self):
        a = np.array([[10.0, 20.0, 15.0]])
        b = np.array([[20.0, 10.0, 15.0]])
        ds = compute_delta_summary(a, b, threshold_db=5.0)
        assert ds["min_delta"] == pytest.approx(-10.0)
        assert ds["max_delta"] == pytest.approx(10.0)
        assert ds["mean_delta"] == pytest.approx(0.0)

    def test_loss_delta_grid_is_a_minus_b(self):
        a = np.array([[5.0, 6.0]])
        b = np.array([[3.0, 8.0]])
        ds = compute_delta_summary(a, b, threshold_db=1.0)
        delta = ds["loss_delta_grid"]
        assert delta[0, 0] == pytest.approx(2.0)
        assert delta[0, 1] == pytest.approx(-2.0)

    def test_valid_mask_excludes_nan_in_either_grid(self):
        a = np.array([[1.0, np.nan, 3.0]])
        b = np.array([[np.nan, 2.0, 3.0]])
        ds = compute_delta_summary(a, b, threshold_db=1.0)
        assert ds["valid_count"] == 1
        assert ds["total_count"] == 1

    def test_large_threshold_classifies_all_as_unchanged(self):
        a = np.array([[5.0, 2.0]])
        b = np.array([[3.0, 4.0]])
        ds = compute_delta_summary(a, b, threshold_db=100.0)
        assert ds["improved"] == 0
        assert ds["degraded"] == 0
        assert ds["unchanged"] == 2

    def test_2d_grids(self):
        a = np.array([[5.0, 2.0], [1.0, 8.0]])
        b = np.array([[1.0, 5.0], [1.0, 2.0]])
        ds = compute_delta_summary(a, b, threshold_db=2.0)
        assert ds["valid_count"] == 4
        assert ds["improved"] == 1
        assert ds["degraded"] == 2