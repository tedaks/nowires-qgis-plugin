# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dataclass for coverage raster grids passed to report payload builders."""

from dataclasses import dataclass

import numpy as np


@dataclass
class CoverageGrids:
    prx_grid: np.ndarray
    loss_grid: np.ndarray
    itm_loss_grid: np.ndarray
    clutter_loss_grid: np.ndarray
    clutter_rx_db_grid: np.ndarray
    bel_rx_db_grid: np.ndarray
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
