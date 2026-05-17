# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np

from ._bilinear import bilinear_sample


def _interpolate_longitudes_shortest(lon1: float, lon2: float, ts: np.ndarray) -> np.ndarray:
    delta = ((lon2 - lon1 + 540.0) % 360.0) - 180.0
    lons = lon1 + ts * delta
    return ((lons + 180.0) % 360.0) - 180.0


def sample_line_from_grid(gd: np.ndarray, gm: dict[str, float], lat1: float, lon1: float, lat2: float, lon2: float, n_pts: int) -> np.ndarray:
    ts = np.linspace(0.0, 1.0, n_pts)
    lats = lat1 + ts * (lat2 - lat1)
    lons = _interpolate_longitudes_shortest(lon1, lon2, ts)
    return bilinear_sample(gd, gm, lats, lons)  # type: ignore[no-any-return]