# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private vector helpers for SAALOS.

Implementation detail of `clutter.saalos`. Not part of the public API.
"""
from __future__ import annotations

import numpy as np

from NoWires.clutter.constants import MAX_CLUTTER_LOSS

# WGS-84 equatorial radius (GRS-80 semi-major axis), in meters.
# Matches the hardcoded 6378137.0 literals in upstream SPLAT/ITWOM
# (itwom3.0.cpp, saalos() at lines 296-315). Deliberately NOT the same
# as constants.EARTH_RADIUS_M (6371000.0, IUGG mean radius) used by the
# rest of the plugin for ITU-R P.526 / 4/3-Earth k-factor math. The ~7 km
# (~0.11%) delta is negligible inside SAALOS's clutter-loss noise floor,
# but keeping this value preserves bit-for-bit parity with the reference
# C implementation. Do not unify with EARTH_RADIUS_M.
EARTH_RADIUS = 6378137.0


def _saalos_vec_above(result, mask, pd, pdk, cch, htx, hrx, hrx_gnd, pol, wn):
    ensa = 1.0
    encca = 1.0
    dp = pd.copy()
    d1a = pd.copy()
    crpc = pd.copy()

    for _ in range(5):
        tde = dp / EARTH_RADIUS
        hc = (cch + EARTH_RADIUS) * (1.0 - np.cos(tde))
        dx = (cch + EARTH_RADIUS) * np.sin(tde)
        ucrpc = np.sqrt((htx - cch + hc) ** 2 + dx * dx)
        ctip = (htx - cch + hc) / ucrpc
        tip = np.arccos(np.clip(ctip, -1.0, 1.0))
        tic = np.maximum(0.0, tip + tde)
        stic = np.sin(tic)
        sta = np.clip((ensa / encca) * stic, -1.0, 1.0)
        ttc = np.arcsin(sta)
        cttc = np.sqrt(1.0 - np.sin(ttc) ** 2)
        crpc = np.where(mask, (cch - hrx) / cttc, crpc)
        crpc = np.where(crpc >= dp, dp - 1.0 / np.maximum(dp, 1.0), crpc)
        d1a = np.where(mask, (crpc * np.sin(ttc)) / (1.0 - 1.0 / EARTH_RADIUS), d1a)
        dp = np.where(mask, pd - d1a, dp)

    ctic = np.cos(tic)
    rsp = np.zeros_like(pd)
    tsp = np.zeros_like(pd)

    ssnps_neg = mask & (tic >= np.pi / 2)
    rsp = np.where(ssnps_neg, 0.997, rsp)
    tsp = np.where(ssnps_neg, 1.0 - 0.997, tsp)
    d1a_fallback = np.minimum(0.1 * pd, 600.0)
    d1a = np.where(ssnps_neg, d1a_fallback, d1a)
    crpc = np.where(ssnps_neg, d1a_fallback, crpc)
    hone = np.where(ssnps_neg, cch + 1.0, htx)

    pol_mask_h = mask & ~ssnps_neg & (pol == 1)
    q_h = np.where(pol_mask_h, (ensa * cttc - encca * ctic) / (ensa * cttc + encca * ctic), 0.0)
    rsp = np.where(pol_mask_h, q_h * q_h, rsp)
    tsp = np.where(pol_mask_h, 1.0 - rsp, tsp)

    pol_mask_v = mask & ~ssnps_neg & (pol == 2)
    q1 = (ensa * ctic - encca * cttc) / (ensa * ctic + encca * cttc)
    q2 = (ensa * cttc - encca * ctic) / (ensa * cttc + encca * ctic)
    rsp = np.where(pol_mask_v, (q1 * q1 + q2 * q2) / 2.0, rsp)
    tsp = np.where(pol_mask_v, 1.0 - rsp, tsp)

    pol_mask_0 = mask & ~ssnps_neg & (pol == 0)
    q_0 = (ensa * ctic - encca * cttc) / (ensa * ctic + encca * cttc)
    rsp = np.where(pol_mask_0, q_0 * q_0, rsp)
    tsp = np.where(pol_mask_0, 1.0 - rsp, tsp)

    hone = np.where(ssnps_neg, cch + 1.0, htx)
    tvsr = np.maximum(0.0, htx - hrx_gnd)

    short = mask & (d1a < 50.0) & ~ssnps_neg
    result[short] = (0.0195 * crpc[short] - 20.0 * np.log10(np.maximum(tsp[short], 1e-30)))

    mid = mask & (d1a >= 50.0) & (d1a < 225.0) & ~ssnps_neg
    q_mid_hi = d1a * (0.03 * np.exp(-0.14 * pdk))
    q_mid_lo = d1a * (0.07 * np.exp(-0.17 * pdk))
    q_mid = np.where(tvsr > 1000.0, q_mid_hi, q_mid_lo)
    result[mid] = (q_mid[mid]
                   + (0.7 * pdk[mid] - np.maximum(0.01, np.log10(wn[mid] * 47.7) - 2.0))
                   * (hrx[mid] / hone[mid]))

    long_d = mask & (d1a >= 225.0) & ~ssnps_neg
    q_base = (0.00055 * pdk
              + np.log10(np.maximum(pdk, 1e-10))
              * (0.041 - 0.0017 * np.sqrt(hone) + 0.019))
    arte_base = d1a * q_base - (18.0 * np.log10(np.maximum(rsp, 1e-30))) / np.exp(hone / 37.5)
    zi = 1.5 * np.sqrt(np.maximum(hone - cch, 0.0))
    pdk_over_zi = pdk > zi
    q_over = ((pdk - zi) * 10.2
              * np.sqrt(np.maximum(0.01, np.log10(wn * 47.7) - 2.0))
              / np.maximum(100.0 - zi, 1.0))
    q_under = (((zi - pdk) / np.maximum(zi, 1e-10))
               * (-20.0 * np.maximum(0.01, np.log10(wn * 47.7) - 2.0))
               / np.sqrt(np.maximum(hone, 1.0)))
    q_extra = np.where(pdk_over_zi, q_over, q_under)
    result[long_d] = arte_base[long_d] + q_extra[long_d]

    ssnps_result = 0.0195 * crpc - 20.0 * np.log10(np.maximum(tsp, 1e-30))
    result[ssnps_neg & mask] = ssnps_result[ssnps_neg & mask]


def _saalos_vec_below(result, mask, pd, pdk, cch, htx, hrx, wn):
    # Below-canopy path: exp(1/cch - htx) matches ITWOM 3.0 itwom3.0.cpp:410
    # and Rust clutterloss-itm-addon-rust/src/lib.rs:186.
    m_cch_h = np.maximum(cch - htx, 1e-10)
    q1 = m_cch_h * (2.06943 - 1.56184 * np.exp(np.clip(1.0 / cch - htx, -700.0, 700.0)))
    q2 = (17.98 - 0.84224 * m_cch_h) * np.exp(-0.00000061 * pd)
    arte = q1 + q2 + 1.34795 * 20.0 * np.log10(pd + 1.0)
    arte -= np.maximum(0.01, np.log10(wn * 47.7) - 2.0) * (hrx / np.maximum(htx, 1e-10))
    result[mask] = arte[mask]
    result[mask & np.isnan(arte)] = MAX_CLUTTER_LOSS
