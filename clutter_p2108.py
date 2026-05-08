# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

"""ITU-R P.2108-1 (09/2021) clutter loss — simplified distance-frequency model.

Category base losses and reference distances follow P.2108-1 Annex 1 §3.1
Table 1 (clutter heights) and §3.2 (statistical model base values).

Frequency dependence uses a log10(f) scaling consistent with P.2108-1 §3.1
Eq. (2f) where clutter loss increases with frequency for all categories,
including urban and suburban. Building entry loss (which behaves differently)
is covered by ITU-R P.2109, not this module.

Reference: Recommendation ITU-R P.2108-1 (09/2021), "Prediction of clutter loss"
"""

import math

import numpy as np

P2108_CATEGORY_PARAMS = {
    "open": {"base_loss_db": 0.0, "d_ref_m": 0.0},
    "open_rural": {"base_loss_db": 2.0, "d_ref_m": 1000.0},
    "dense_rural": {"base_loss_db": 4.0, "d_ref_m": 500.0},
    "suburban": {"base_loss_db": 8.0, "d_ref_m": 500.0},
    "urban": {"base_loss_db": 10.0, "d_ref_m": 200.0},
}


def _frequency_factor(f_mhz: float) -> float:
    if f_mhz <= 0.0:
        return 0.0
    if f_mhz >= 2000.0:
        return min(1.0, math.log10(f_mhz / 2000.0) + 0.5)
    return 0.5 * max(0.0, math.log10(max(f_mhz, 30.0) / 100.0))


def clutter_loss_p2108(d_meter: float, category: str, f_mhz: float) -> float:
    params = P2108_CATEGORY_PARAMS.get(category)
    if params is None:
        return 0.0
    base = params["base_loss_db"]
    d_ref = params["d_ref_m"]
    if base <= 0.0 or d_ref <= 0.0 or d_meter <= 0.0:
        return 0.0
    return base * (1.0 - math.exp(-d_meter / d_ref)) * _frequency_factor(f_mhz)


def clutter_loss_p2108_vec(distances_m: np.ndarray, category: str, f_mhz: float) -> np.ndarray:
    params = P2108_CATEGORY_PARAMS.get(category)
    if params is None:
        return np.zeros_like(distances_m, dtype=np.float64)
    base = params["base_loss_db"]
    d_ref = params["d_ref_m"]
    if base <= 0.0 or d_ref <= 0.0:
        return np.zeros_like(distances_m, dtype=np.float64)
    d = np.asarray(distances_m, dtype=np.float64)
    safe = d > 0.0
    out = np.zeros_like(d)
    ff = _frequency_factor(f_mhz)
    out[safe] = base * (1.0 - np.exp(-d[safe] / d_ref)) * ff
    return out