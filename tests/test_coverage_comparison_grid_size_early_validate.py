# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest


@pytest.mark.qgis_integration
def test_grid_size_validation_precedes_dem_download():
    """Behavioral: mismatched grid sizes cause early failure before downloads."""
    from qgis.core import QgsProcessingException

    from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm

    alg = CoverageComparisonAlgorithm()
    alg.initAlgorithm({})

    params = {
        "PANEL_A_GRID_SIZE": 1,
        "PANEL_B_GRID_SIZE": 2,
        "OUTPUT_DELTA": "memory",
    }
    with pytest.raises(QgsProcessingException, match="must match"):
        alg.processAlgorithm(params, None, None)
