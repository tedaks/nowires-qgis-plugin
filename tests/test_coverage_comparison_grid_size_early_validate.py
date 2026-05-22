# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import inspect


def test_grid_size_validation_precedes_dem_download():
    from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm
    src = inspect.getsource(CoverageComparisonAlgorithm.processAlgorithm)
    grid_check_pos = src.find("must match")
    dem_download_pos = src.find("ensure_dem_for_area")
    assert grid_check_pos < dem_download_pos, (
        "Grid size validation should occur before DEM download"
    )