# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


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
    n_rows = gm["n_lat"]
    n_cols = gm["n_lon"]
    d_lat = (gm["max_lat"] - gm["min_lat"]) / n_rows
    d_lon = (gm["max_lon"] - gm["min_lon"]) / n_cols
    fy = (gm["max_lat"] - lat) / d_lat - 0.5
    fx = (lon - gm["min_lon"]) / d_lon - 0.5
    if fy < -0.5 or fx < -0.5 or fy > n_rows - 0.5 or fx > n_cols - 0.5:
        logger.debug("Bilinear sample out of bounds: lat=%s lon=%s", lat, lon)
        return float("nan")
    fy = max(0.0, min(n_rows - 1.0 - 1e-9, fy))
    fx = max(0.0, min(n_cols - 1.0 - 1e-9, fx))
    y0 = int(fy)
    x0 = int(fx)
    y1 = min(y0 + 1, n_rows - 1)
    x1 = min(x0 + 1, n_cols - 1)
    ty = fy - y0
    tx = fx - x0
    v00 = data[y0, x0]
    v01 = data[y0, x1]
    v10 = data[y1, x0]
    v11 = data[y1, x1]
    return (  # type: ignore[no-any-return]  # numpy scalar blend types as Any
        v00 * (1 - tx) * (1 - ty)
        + v01 * tx * (1 - ty)
        + v10 * (1 - tx) * ty
        + v11 * tx * ty
    )


def _bilinear_line(data: np.ndarray, gm: dict, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (gm["max_lat"] - gm["min_lat"]) / n_lat
    d_lon = (gm["max_lon"] - gm["min_lon"]) / n_lon
    fy_raw = (gm["max_lat"] - lats) / d_lat - 0.5
    fx_raw = (lons - gm["min_lon"]) / d_lon - 0.5
    oob = (
        (fy_raw < -0.5) | (fx_raw < -0.5)
        | (fy_raw > n_lat - 0.5) | (fx_raw > n_lon - 0.5)
    )
    if np.any(oob):
        logger.debug("Bilinear line sample: %d of %d out of bounds", int(np.sum(oob)), oob.size)
    fy = np.clip(fy_raw, 0.0, n_lat - 1.0 - 1e-9)
    fx = np.clip(fx_raw, 0.0, n_lon - 1.0 - 1e-9)
    y0 = np.floor(fy).astype(np.int32)
    x0 = np.floor(fx).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, n_lat - 1)
    x1 = np.clip(x0 + 1, 0, n_lon - 1)
    ty = (fy - y0).astype(np.float32)
    tx_ = (fx - x0).astype(np.float32)
    result = (
        data[y0, x0] * (1 - tx_) * (1 - ty)
        + data[y0, x1] * tx_ * (1 - ty)
        + data[y1, x0] * (1 - tx_) * ty
        + data[y1, x1] * tx_ * ty
    )
    result[oob] = np.nan
    return result  # type: ignore[no-any-return]  # numpy bilinear-blend result types as Any


def _bilinear_grid(data: np.ndarray, gm: dict, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (gm["max_lat"] - gm["min_lat"]) / n_lat
    d_lon = (gm["max_lon"] - gm["min_lon"]) / n_lon
    fy_raw = (gm["max_lat"] - lats) / d_lat - 0.5
    fx_raw = (lons - gm["min_lon"]) / d_lon - 0.5
    oob = (
        (fy_raw < -0.5) | (fx_raw < -0.5)
        | (fy_raw > n_lat - 0.5) | (fx_raw > n_lon - 0.5)
    )
    if np.any(oob):
        logger.debug("Bilinear grid sample: %d of %d out of bounds", int(np.sum(oob)), oob.size)
    fy = np.clip(fy_raw, 0.0, n_lat - 1.0 - 1e-9)
    fx = np.clip(fx_raw, 0.0, n_lon - 1.0 - 1e-9)
    y0 = np.floor(fy).astype(np.int32)
    x0 = np.floor(fx).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, n_lat - 1)
    x1 = np.clip(x0 + 1, 0, n_lon - 1)
    ty = (fy - y0).astype(np.float32)
    tx_ = (fx - x0).astype(np.float32)
    result = (
        data[y0, x0] * (1 - tx_) * (1 - ty)
        + data[y0, x1] * tx_ * (1 - ty)
        + data[y1, x0] * (1 - tx_) * ty
        + data[y1, x1] * tx_ * ty
    ).astype(np.float32)
    result[oob] = np.nan
    return result  # type: ignore[no-any-return]  # numpy bilinear-blend result types as Any
