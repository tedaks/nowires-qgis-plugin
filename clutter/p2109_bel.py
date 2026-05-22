# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

"""ITU-R P.2109-2 — Building Entry Loss.

Validity: 0.08–100 GHz, building type 'traditional' or 'thermally_efficient',
elevation angle theta at facade (degrees above horizontal), probability P (0–100).
"""

import logging
import math

import numpy as np

from NoWires.clutter.context import BuildingType
from NoWires.clutter.p2108_common import f_inv_normal, validate_frequency_ghz

logger = logging.getLogger(__name__)

_FREQ_MIN_GHZ = 0.08
_FREQ_MAX_GHZ = 100.0

_COEFFS: dict[BuildingType, dict[str, float]] = {
    "traditional": {
        "r": 12.64, "s": 3.72, "t": 0.96,
        "u": 9.6, "v": 2.0,
        "w": 9.1, "x": -3.0,
        "y": 4.5, "z": -2.0,
    },
    "thermally_efficient": {
        "r": 28.19, "s": -3.00, "t": 8.48,
        "u": 13.5, "v": 3.8,
        "w": 27.8, "x": -2.9,
        "y": 9.4, "z": -2.1,
    },
}

_C = -3.0


def building_entry_loss(f_ghz, building_type: BuildingType = "traditional", theta_deg=0.0, p=50.0):
    """P.2109-2 building entry loss (dB).

    Args:
        f_ghz: Frequency in GHz (0.08–100).
        building_type: 'traditional' or 'thermally_efficient'.
        theta_deg: Elevation angle at facade in degrees (default 0 = horizontal).
        p: Percentage probability (0.01–99.99).

    Returns:
        Building entry loss in dB (always >= 0).
    """
    f_ghz, f_clamped = validate_frequency_ghz(f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    if f_clamped:
        logger.info("P.2109-2: frequency %.3f GHz clamped to %.2f–%.2f GHz",
                     f_ghz, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    coeffs = _COEFFS.get(building_type)
    if coeffs is None:
        logger.warning(
            "P.2109-2: unknown building type '%s', defaulting to traditional",
            building_type)
        coeffs = _COEFFS["traditional"]
    theta_deg = max(0.0, min(abs(theta_deg), 90.0))
    log_f = math.log10(f_ghz)
    L_h = coeffs["r"] + coeffs["s"] * log_f + coeffs["t"] * log_f ** 2
    L_e = 0.212 * abs(theta_deg)
    mu1 = L_h + L_e
    mu2 = coeffs["w"] + coeffs["x"] * log_f
    sigma1 = coeffs["u"] + coeffs["v"] * log_f
    sigma2 = coeffs["y"] + coeffs["z"] * log_f
    F_inv = f_inv_normal(p)
    A = F_inv * sigma1 + mu1
    B = F_inv * sigma2 + mu2
    L_BEL = 10.0 * math.log10(
        10.0 ** (0.1 * A) + 10.0 ** (0.1 * B) + 10.0 ** (0.1 * _C)
    )
    return max(0.0, L_BEL)


def building_entry_loss_vec(f_ghz_arr, building_type: BuildingType = "traditional", theta_deg=0.0, p=50.0):
    """Vectorized P.2109-2 building entry loss.

    Args:
        f_ghz_arr: Array of frequencies in GHz.
        building_type: 'traditional' or 'thermally_efficient'.
        theta_deg: Elevation angle at facade in degrees.
        p: Percentage probability.

    Returns:
        ndarray of BEL in dB.
    """
    f_arr = np.asarray(f_ghz_arr, dtype=np.float64)
    f_clamped = np.clip(f_arr, _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    if np.any(f_arr != f_clamped):
        logger.info("P.2109-2 vec: some frequencies clamped to %.2f–%.2f GHz",
                     _FREQ_MIN_GHZ, _FREQ_MAX_GHZ)
    coeffs = _COEFFS.get(building_type, _COEFFS["traditional"])
    log_f = np.log10(f_clamped)
    L_h = coeffs["r"] + coeffs["s"] * log_f + coeffs["t"] * log_f ** 2
    L_e = 0.212 * abs(theta_deg)
    mu1 = L_h + L_e
    mu2 = coeffs["w"] + coeffs["x"] * log_f
    sigma1 = coeffs["u"] + coeffs["v"] * log_f
    sigma2 = coeffs["y"] + coeffs["z"] * log_f
    F_inv = f_inv_normal(p)
    A = F_inv * sigma1 + mu1
    B = F_inv * sigma2 + mu2
    L_BEL = 10.0 * np.log10(
        10.0 ** (0.1 * A) + 10.0 ** (0.1 * B) + 10.0 ** (0.1 * _C)
    )
    return np.maximum(0.0, L_BEL)