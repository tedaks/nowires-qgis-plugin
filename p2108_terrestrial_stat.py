# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

"""ITU-R P.2108-1 Section 3.2 — Statistical clutter loss for terrestrial paths.

Validity: 0.5–67 GHz, min path length 0.25 km (one end) or 1.0 km (both ends),
percentage locations 0 < p < 100.
Single combined urban+suburban model — not per-category.
"""

import logging
import math

import numpy as np

from NoWires.p2108_common import q_inv_complementary_normal, validate_distance_km, validate_frequency_ghz

logger = logging.getLogger(__name__)

_FREQ_MIN_GHZ = 0.5
_FREQ_MAX_GHZ = 67.0
_DIST_MIN_KM = 0.25
_DIST_CAP_KM = 2.0
_Sigma_L = 4.0
_Sigma_S = 6.0


def _L_l(f_ghz):
    return -2.0 * math.log10(10.0 ** (-5.0 * math.log10(f_ghz) - 12.5) + 10.0 ** (-16.5))


def _L_s(d_km, f_ghz):
    return 32.98 + 23.9 * math.log10(d_km) + 3.0 * math.log10(f_ghz)


def _sigma_cb(L_l_val, L_s_val):
    w_l = 10.0 ** (-0.2 * L_l_val)
    w_s = 10.0 ** (-0.2 * L_s_val)
    return math.sqrt((_Sigma_L ** 2 * w_l + _Sigma_S ** 2 * w_s) / (w_l + w_s))


def clutter_loss_p2108_terrestrial_stat(d_km, f_ghz, p=50.0):
    """P.2108-1 Section 3.2 statistical clutter loss (dB).

    Args:
        d_km: Path length in km (>= 0.25).
        f_ghz: Frequency in GHz (0.5–67).
        p: Percentage of locations (0 < p < 100).

    Returns:
        Clutter loss in dB. Capped at d=2 km per eq. (6).
    """
    f_ghz, f_clamped = validate_frequency_ghz(f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    if f_clamped:
        logger.info("P.2108-1 §3.2: frequency %.3f GHz clamped to %.3f–%.3f GHz",
                     f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    d_km, d_clamped = validate_distance_km(d_km, min_km=_DIST_MIN_KM)
    if d_clamped:
        logger.info("P.2108-1 §3.2: distance %.3f km clamped to min %.3f km", d_km, _DIST_MIN_KM)
    L_l_val = _L_l(f_ghz)
    L_s_val = _L_s(d_km, f_ghz)
    sigma_cb = _sigma_cb(L_l_val, L_s_val)
    q_inv = q_inv_complementary_normal(p)
    result = -5.0 * math.log10(10.0 ** (-0.2 * L_l_val) + 10.0 ** (-0.2 * L_s_val))
    result -= sigma_cb * q_inv
    result = max(result, 0.0)
    L_cap = _compute_capped(f_ghz, p)
    return min(result, L_cap)


def _compute_capped(f_ghz, p=50.0):
    L_l_val = _L_l(f_ghz)
    L_s_val = _L_s(_DIST_CAP_KM, f_ghz)
    sigma_cb = _sigma_cb(L_l_val, L_s_val)
    q_inv = q_inv_complementary_normal(p)
    result = -5.0 * math.log10(10.0 ** (-0.2 * L_l_val) + 10.0 ** (-0.2 * L_s_val))
    result -= sigma_cb * q_inv
    return max(result, 0.0)


def clutter_loss_p2108_terrestrial_stat_vec(d_km_arr, f_ghz, p=50.0):
    """Vectorized version of P.2108-1 Section 3.2 clutter loss."""
    f_ghz, f_clamped = validate_frequency_ghz(f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    if f_clamped:
        logger.info("P.2108-1 §3.2 vec: frequency clamped to %.3f–%.3f GHz",
                     _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    d = np.asarray(d_km_arr, dtype=np.float64)
    d = np.clip(d, _DIST_MIN_KM, None)
    L_l_val = _L_l(f_ghz)
    w_l = 10.0 ** (-0.2 * L_l_val)
    L_s_vals = 32.98 + 23.9 * np.log10(d) + 3.0 * np.log10(f_ghz)
    w_s = 10.0 ** (-0.2 * L_s_vals)
    sigma_cb = np.sqrt((_Sigma_L ** 2 * w_l + _Sigma_S ** 2 * w_s) / (w_l + w_s))
    q_inv = q_inv_complementary_normal(p)
    result = -5.0 * np.log10(w_l + w_s) - sigma_cb * q_inv
    result = np.maximum(result, 0.0)
    L_cap = _compute_capped(f_ghz, p)
    result = np.minimum(result, L_cap)
    return result