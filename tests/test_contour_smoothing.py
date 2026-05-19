# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for contour_smoothing pure-logic functions."""


from contour.smoothing import _gaussian_kernel_2d


class TestGaussianKernel2d:
    def test_output_has_correct_number_of_coefficients(self):
        for size in (3, 5, 7, 13):
            coefs = _gaussian_kernel_2d(size)
            assert len(coefs.split()) == size * size

    def test_coefficients_sum_to_one(self):
        for size in (3, 5, 7):
            coefs = _gaussian_kernel_2d(size)
            total = sum(float(c) for c in coefs.split())
            assert abs(total - 1.0) < 1e-4

    def test_center_coefficient_is_largest(self):
        coefs = _gaussian_kernel_2d(3)
        vals = [float(c) for c in coefs.split()]
        center = vals[4]
        assert center == max(vals)

    def test_kernel_is_symmetric(self):
        coefs = _gaussian_kernel_2d(5)
        vals = [float(c) for c in coefs.split()]
        size = 5
        for y in range(size):
            for x in range(size):
                mirror_x = size - 1 - x
                mirror_y = size - 1 - y
                assert abs(vals[y * size + x] - vals[mirror_y * size + mirror_x]) < 1e-10

    def test_default_sigma_covers_three_sigma(self):
        size = 7
        coefs = _gaussian_kernel_2d(size)
        corner = float(coefs.split()[0])
        center = float(coefs.split()[size // 2 * size + size // 2])
        assert corner < center * 0.01

    def test_custom_sigma_changes_spread(self):
        narrow = _gaussian_kernel_2d(7, sigma=0.5)
        wide = _gaussian_kernel_2d(7, sigma=3.0)
        narrow_vals = [float(c) for c in narrow.split()]
        wide_vals = [float(c) for c in wide.split()]
        center_idx = 7 // 2 * 7 + 7 // 2
        assert narrow_vals[center_idx] > wide_vals[center_idx]

    def test_size_3_kernel_values(self):
        coefs = _gaussian_kernel_2d(3)
        vals = [float(c) for c in coefs.split()]
        assert len(vals) == 9
        assert abs(sum(vals) - 1.0) < 1e-4
        center = vals[4]
        edge_mid = vals[1]
        corner = vals[0]
        assert center > edge_mid > corner