# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""ITU-R P.2108-1 Section 3.1 — Height-gain terminal correction.

Validity: 0.03–3 GHz, antenna height h below representative clutter height R.
Per-category from P.2108-1 Table 3.
Not a function of distance or percentile — only h, f, R, w_s.
"""

from __future__ import annotations

import logging
import math

import numpy as np

from NoWires.clutter.categories import CLUTTER_CATEGORY_PARAMS
from NoWires.clutter.p2108_common import validate_frequency_ghz

logger = logging.getLogger(__name__)

_FREQ_MIN_GHZ = 0.03
_FREQ_MAX_GHZ = 3.0
_DEFAULT_STREET_WIDTH_M = 27.0
_MIN_HEIGHT_M = 0.1

_CATEGORY_PARAMS: dict[str, dict[str, int | float | str]] = {
    cat: {"R_m": params["R_m"], "method": params["p2108_3_1_method"]}
    for cat, params in CLUTTER_CATEGORY_PARAMS.items()
}


def _J_nu(nu: float) -> float:
    if nu <= -0.78:
        return 0.0
    return 6.9 + 20.0 * math.log10(
        math.sqrt((nu - 0.1) ** 2 + 1.0) + nu - 0.1
    )


def _J_nu_vec(nu_arr):
    out = np.zeros_like(nu_arr, dtype=np.float64)
    mask = nu_arr > -0.78
    nu_m = nu_arr[mask]
    out[mask] = 6.9 + 20.0 * np.log10(
        np.sqrt((nu_m - 0.1) ** 2 + 1.0) + nu_m - 0.1
    )
    return out


def height_gain_loss(h_m: float, f_ghz: float, category: str,
                    w_s_m: float = _DEFAULT_STREET_WIDTH_M) -> float:
    """P.2108-1 §3.1 height-gain terminal correction (dB).

    Args:
        h_m: Antenna height AGL in metres (must be below R for non-zero result).
        f_ghz: Frequency in GHz (0.03–3).
        category: Plugin category string (open, open_rural, dense_rural,
                  vegetation, suburban, urban).
        w_s_m: Street width in metres (default 27).

    Returns:
        Ah in dB (always >= 0; returns 0 if h >= R or category is open).
    """
    f_ghz, f_clamped = validate_frequency_ghz(f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    if f_clamped:
        logger.info("P.2108-1 §3.1: frequency %.3f GHz clamped to %.2f–%.2f GHz",
                     f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    params = _CATEGORY_PARAMS.get(category)
    if params is None or category == "open":
        return 0.0
    R = float(params["R_m"])
    method = str(params["method"])
    if h_m < _MIN_HEIGHT_M or h_m >= R:
        return 0.0
    h_dif = R - h_m
    theta_clut = math.degrees(math.atan(h_dif / w_s_m))
    K_nu = 0.342 * math.sqrt(f_ghz)
    nu = K_nu * math.sqrt(h_dif * theta_clut)
    if method == "2a":
        J = _J_nu(nu)
        return max(0.0, J - 6.03)
    if h_m <= 0.0 or R <= 0.0:
        return 0.0
    Kh2 = 21.8 + 6.2 * math.log10(f_ghz)
    Ah = -Kh2 * math.log10(h_m / R)
    return max(0.0, Ah)


def height_gain_loss_vec(h_m_arr, f_ghz, categories, w_s_m=_DEFAULT_STREET_WIDTH_M):
    """Vectorized P.2108-1 §3.1 height-gain terminal correction.

    Args:
        h_m_arr: Array of antenna heights AGL in metres.
        f_ghz: Frequency in GHz.
        categories: Array-like of category strings (same length as h_m_arr).
        w_s_m: Street width in metres.

    Returns:
        ndarray of Ah in dB.
    """
    f_ghz, f_clamped = validate_frequency_ghz(f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    if f_clamped:
        logger.info("P.2108-1 §3.1 vec: frequency clamped to %.2f–%.2f GHz",
                     _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    h = np.asarray(h_m_arr, dtype=np.float64)
    cats = np.asarray(categories, dtype=object)
    out = np.zeros_like(h, dtype=np.float64)
    for cat_name in np.unique(cats):
        params = _CATEGORY_PARAMS.get(cat_name)
        if params is None or cat_name == "open":
            continue
        R = float(params["R_m"])
        method = params["method"]
        mask = (cats == cat_name) & (h >= _MIN_HEIGHT_M) & (h < R)
        if not mask.any():
            continue
        h_dif = R - h[mask]
        theta_clut = np.degrees(np.arctan(h_dif / w_s_m))
        K_nu = 0.342 * math.sqrt(f_ghz)
        nu = K_nu * np.sqrt(h_dif * theta_clut)
        if method == "2a":
            Ah = _J_nu_vec(nu) - 6.03
            out[mask] = np.maximum(0.0, Ah)
        else:
            Kh2 = 21.8 + 6.2 * math.log10(f_ghz)
            safe_h = np.maximum(h[mask], 1e-30)
            Ah = -Kh2 * np.log10(safe_h / R)
            out[mask] = np.maximum(0.0, Ah)
    return out
