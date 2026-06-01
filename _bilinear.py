# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def _compute_indices(gm: dict, lats: np.ndarray, lons: np.ndarray):
    n_rows = gm["n_lat"]
    n_cols = gm["n_lon"]
    d_lat = (gm["max_lat"] - gm["min_lat"]) / n_rows
    d_lon = (gm["max_lon"] - gm["min_lon"]) / n_cols
    fy_raw = (gm["max_lat"] - lats) / d_lat - 0.5
    fx_raw = (lons - gm["min_lon"]) / d_lon - 0.5
    oob = (
        (fy_raw < -0.5) | (fx_raw < -0.5)
        | (fy_raw > n_rows - 0.5) | (fx_raw > n_cols - 0.5)
    )
    fy = np.clip(fy_raw, 0.0, n_rows - 1.0 - 1e-9)
    fx = np.clip(fx_raw, 0.0, n_cols - 1.0 - 1e-9)
    y0 = np.floor(fy).astype(np.int32)
    x0 = np.floor(fx).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, n_rows - 1)
    x1 = np.clip(x0 + 1, 0, n_cols - 1)
    ty = (fy - y0).astype(np.float64)
    tx = (fx - x0).astype(np.float64)
    return y0, x0, y1, x1, ty, tx, oob


def bilinear_sample(data: np.ndarray, grid_meta: dict, lats, lons):
    if isinstance(lats, (int, float)):
        return _bilinear_scalar(data, grid_meta, float(lats), float(lons))
    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)
    return _bilinear_line(data, grid_meta, lats, lons)


def bilinear_sample_grid(data: np.ndarray, grid_meta: dict, lats, lons):
    lats_arr = np.asarray(lats, dtype=np.float64)[:, np.newaxis]
    lons_arr = np.asarray(lons, dtype=np.float64)[np.newaxis, :]
    return _bilinear_grid(data, grid_meta, lats_arr, lons_arr)


def _bilinear_scalar(data: np.ndarray, gm: dict, lat: float, lon: float) -> float:
    lats = np.array([lat], dtype=np.float64)
    lons_ = np.array([lon], dtype=np.float64)
    y0, x0, y1, x1, ty, tx, oob = _compute_indices(gm, lats, lons_)
    if bool(oob[0]):
        logger.debug("Bilinear sample out of bounds: lat=%s lon=%s", lat, lon)
        return float("nan")
    iy0, ix0, iy1, ix1 = int(y0[0]), int(x0[0]), int(y1[0]), int(x1[0])
    t_y, t_x = float(ty[0]), float(tx[0])
    v00 = data[iy0, ix0]
    v01 = data[iy0, ix1]
    v10 = data[iy1, ix0]
    v11 = data[iy1, ix1]
    return (  # type: ignore[no-any-return]
        v00 * (1 - t_x) * (1 - t_y)
        + v01 * t_x * (1 - t_y)
        + v10 * (1 - t_x) * t_y
        + v11 * t_x * t_y
    )


def _bilinear_line(data: np.ndarray, gm: dict, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    y0, x0, y1, x1, ty, tx_, oob = _compute_indices(gm, lats, lons)
    if np.any(oob):
        logger.debug("Bilinear line sample: %d of %d out of bounds", int(np.sum(oob)), oob.size)
    result = (
        data[y0, x0] * (1 - tx_) * (1 - ty)
        + data[y0, x1] * tx_ * (1 - ty)
        + data[y1, x0] * (1 - tx_) * ty
        + data[y1, x1] * tx_ * ty
    )
    result[oob] = np.nan
    return result  # type: ignore[no-any-return]


def _bilinear_grid(data: np.ndarray, gm: dict, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    y0, x0, y1, x1, ty, tx_, oob = _compute_indices(gm, lats, lons)
    if np.any(oob):
        logger.debug("Bilinear grid sample: %d of %d out of bounds", int(np.sum(oob)), oob.size)
    result = (
        data[y0, x0] * (1 - tx_) * (1 - ty)
        + data[y0, x1] * tx_ * (1 - ty)
        + data[y1, x0] * (1 - tx_) * ty
        + data[y1, x1] * tx_ * ty
    )
    result[oob] = np.nan
    return result  # type: ignore[no-any-return]
