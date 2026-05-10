# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for bundled ITM terrain helpers."""

import numpy as np
import pytest

from itm.models import TerrainProfile
from itm.terrain import find_horizons


def test_find_horizons_accepts_two_point_los_profile():
    elevations = np.array([100.0, 101.0], dtype=float)
    resolution = 30.0
    a_e = 8_500_000.0

    theta_hzn, d_hzn = find_horizons(
        elevations=elevations,
        resolution=resolution,
        h__meter=(10.0, 10.0),
        a_e__meter=a_e,
    )

    expected_tx = 1.0 / resolution - resolution / (2.0 * a_e)
    expected_rx = -1.0 / resolution - resolution / (2.0 * a_e)
    assert theta_hzn == pytest.approx([expected_tx, expected_rx])
    assert d_hzn == pytest.approx([resolution, resolution])


def test_truncated_pfl_that_leaves_two_points_still_has_valid_horizons():
    terrain = TerrainProfile.from_pfl([5.0, 30.0, 100.0, 101.0])

    theta_hzn, d_hzn = find_horizons(
        terrain.elevations,
        terrain.resolution,
        h__meter=(10.0, 10.0),
        a_e__meter=8_500_000.0,
    )

    assert len(theta_hzn) == 2
    assert d_hzn == pytest.approx([30.0, 30.0])
