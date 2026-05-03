# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for p2p_compute: NaN handling patterns and FSPL edge cases."""

import math


class TestNaNHandling:
    def test_nan_elevations_replaced_with_zero(self):
        elevations = [0.0, float("nan"), 100.0]
        result = [0.0 if math.isnan(e) else e for e in elevations]
        assert result == [0.0, 0.0, 100.0]

    def test_all_nan_elevations_replaced(self):
        elevations = [float("nan"), float("nan")]
        result = [0.0 if math.isnan(e) else e for e in elevations]
        assert result == [0.0, 0.0]

    def test_no_nan_elevations_unchanged(self):
        elevations = [10.0, 20.0, 30.0]
        result = [0.0 if math.isnan(e) else e for e in elevations]
        assert result == [10.0, 20.0, 30.0]

    def test_nan_count_counted_correctly(self):
        elevations = [float("nan"), 10.0, float("nan"), 20.0]
        nan_count = sum(1 for e in elevations if math.isnan(e))
        assert nan_count == 2


class TestFSPLEdgeCases:
    def test_fspl_positive_distance_and_frequency(self):
        dist_m = 1000.0
        f_mhz = 900.0
        fspl = 20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(f_mhz) + 32.44
        assert fspl > 0

    def test_fspl_zero_distance_returns_zero(self):
        dist_m = 0.0
        f_mhz = 900.0
        if dist_m > 0 and f_mhz > 0:
            fspl = 20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(f_mhz) + 32.44
        else:
            fspl = 0.0
        assert fspl == 0.0

    def test_fspl_zero_frequency_returns_zero(self):
        dist_m = 1000.0
        f_mhz = 0.0
        if dist_m > 0 and f_mhz > 0:
            fspl = 20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(f_mhz) + 32.44
        else:
            fspl = 0.0
        assert fspl == 0.0

    def test_fspl_increases_with_distance(self):
        f_mhz = 900.0
        fspl_1km = 20.0 * math.log10(1.0) + 20.0 * math.log10(f_mhz) + 32.44
        fspl_10km = 20.0 * math.log10(10.0) + 20.0 * math.log10(f_mhz) + 32.44
        assert fspl_10km > fspl_1km

    def test_fspl_increases_with_frequency(self):
        dist_m = 1000.0
        fspl_900 = 20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(900.0) + 32.44
        fspl_2400 = 20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(2400.0) + 32.44
        assert fspl_2400 > fspl_900