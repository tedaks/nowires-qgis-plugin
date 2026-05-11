# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np


def _interpolate_longitudes_shortest(lon1, lon2, ts) -> np.ndarray:
    delta = ((lon2 - lon1 + 540.0) % 360.0) - 180.0
    lons = lon1 + ts * delta
    return ((lons + 180.0) % 360.0) - 180.0


def sample_line_from_grid(gd, gm, lat1, lon1, lat2, lon2, n_pts):
    min_lat = gm["min_lat"]
    max_lat = gm["max_lat"]
    min_lon = gm["min_lon"]
    max_lon = gm["max_lon"]
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (max_lat - min_lat) / n_lat
    d_lon = (max_lon - min_lon) / n_lon

    ts = np.linspace(0.0, 1.0, n_pts)
    lats = lat1 + ts * (lat2 - lat1)
    lons = _interpolate_longitudes_shortest(lon1, lon2, ts)

    fy_raw = (max_lat - lats) / d_lat - 0.5
    fx_raw = (lons - min_lon) / d_lon - 0.5
    oob = (fy_raw < -0.5) | (fx_raw < -0.5) | (fy_raw > n_lat - 0.5) | (fx_raw > n_lon - 0.5)
    fy = np.clip(fy_raw, 0.0, n_lat - 1.0 - 1e-9)
    fx = np.clip(fx_raw, 0.0, n_lon - 1.0 - 1e-9)

    y0 = np.floor(fy).astype(np.int32)
    x0 = np.floor(fx).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, n_lat - 1)
    x1 = np.clip(x0 + 1, 0, n_lon - 1)
    ty = (fy - y0).astype(np.float32)
    tx_ = (fx - x0).astype(np.float32)

    result = (
        gd[y0, x0] * (1 - tx_) * (1 - ty)
        + gd[y0, x1] * tx_ * (1 - ty)
        + gd[y1, x0] * (1 - tx_) * ty
        + gd[y1, x1] * tx_ * ty
    )
    result[oob] = np.nan
    return result