# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import math

import numpy as np

from .clutter_constants import MAX_CLUTTER_LOSS

EARTH_RADIUS = 6378137.0


def clutter_loss_saalos(d__meter, cch__meter, h_tx__meter, h_rx__meter,
                        h_rx_gnd__meter, pol, f__mhz):
    if cch__meter <= 0.0:
        return 0.0
    if d__meter == 0.0:
        return 0.0
    if h_rx__meter > cch__meter:
        return 0.0

    wn = f__mhz / 47.7
    pd = d__meter
    pdk = pd / 1000.0

    hone = h_tx__meter
    arte = 0.0

    if h_tx__meter > cch__meter:
        ensa = 1.0
        encca = 1.0
        dp = pd
        d1a = pd
        crpc = pd
        cttc = 1.0
        ssnps = 0.0
        ctic = 1.0
        ttc = 0.0
        tic = 0.0
        tsp = 1.0
        rsp = 0.0

        for _ in range(5):
            tde = dp / EARTH_RADIUS
            hc = (cch__meter + EARTH_RADIUS) * (1.0 - math.cos(tde))
            dx = (cch__meter + EARTH_RADIUS) * math.sin(tde)
            ucrpc = math.sqrt((hone - cch__meter + hc) ** 2 + dx * dx)
            ctip = (hone - cch__meter + hc) / ucrpc
            tip = math.acos(ctip)
            tic = max(0.0, tip + tde)
            stic = math.sin(tic)
            sta = (ensa / encca) * stic
            ttc = math.asin(sta)
            cttc = math.sqrt(1.0 - math.sin(ttc) ** 2)
            crpc = (cch__meter - h_rx__meter) / cttc
            if crpc >= dp:
                crpc = dp - 1.0 / dp
            ssnps = (math.pi / 2.0) - tic
            d1a = (crpc * math.sin(ttc)) / (1.0 - 1.0 / EARTH_RADIUS)
            dp = pd - d1a

        ctic = math.cos(tic)

        if ssnps <= 0.0:
            d1a = min(0.1 * pd, 600.0)
            crpc = d1a
            hone = cch__meter + 1.0
            rsp = 0.997
            tsp = 1.0 - rsp
        elif pol == 1:
            q = (ensa * cttc - encca * ctic) / (ensa * cttc + encca * ctic)
            rsp = q * q
            tsp = 1.0 - rsp
        elif pol == 2:
            q1 = (ensa * ctic - encca * cttc) / (ensa * ctic + encca * cttc)
            q2 = (ensa * cttc - encca * ctic) / (ensa * cttc + encca * ctic)
            rsp = (q1 * q1 + q2 * q2) / 2.0
            tsp = 1.0 - rsp
        else:
            q = (ensa * ctic - encca * cttc) / (ensa * ctic + encca * ctic)
            rsp = q * q
            tsp = 1.0 - rsp

        tvsr = max(0.0, h_tx__meter - h_rx_gnd__meter)

        if d1a < 50.0:
            arte = 0.0195 * crpc - 20.0 * math.log10(tsp)
        elif d1a < 225.0:
            if tvsr > 1000.0:
                q = d1a * (0.03 * math.exp(-0.14 * pdk))
            else:
                q = d1a * (0.07 * math.exp(-0.17 * pdk))
            arte = q + (0.7 * pdk - max(0.01, math.log10(wn * 47.7) - 2.0)) * (h_rx__meter / hone)
        else:
            q = 0.00055 * pdk + math.log10(pdk) * (0.041 - 0.0017 * math.sqrt(hone) + 0.019)
            arte = d1a * q - (18.0 * math.log10(rsp)) / math.exp(hone / 37.5)
            zi = 1.5 * math.sqrt(hone - cch__meter)
            if pdk > zi:
                q = ((pdk - zi) * 10.2 *
                     math.sqrt(max(0.01, math.log10(wn * 47.7) - 2.0)) /
                     (100.0 - zi))
            else:
                q = ((zi - pdk) / zi) * (
                    -20.0 * max(0.01, math.log10(wn * 47.7) - 2.0)
                ) / math.sqrt(hone)
            arte = arte + q
    else:
        q1 = (cch__meter - h_tx__meter) * (
            2.06943 - 1.56184 * math.exp(1.0 / cch__meter - h_tx__meter))
        q2 = (17.98 - 0.84224 * (cch__meter - h_tx__meter)) * math.exp(-0.00000061 * pd)
        arte = q1 + q2 + 1.34795 * 20.0 * math.log10(pd + 1.0)
        arte -= max(0.01, math.log10(wn * 47.7) - 2.0) * (h_rx__meter / h_tx__meter)

    if arte < 0.0:
        return 0.0
    if arte > MAX_CLUTTER_LOSS:
        return MAX_CLUTTER_LOSS
    return arte


def clutter_loss_saalos_vec(d_meter, cch_meter, h_tx_meter, h_rx_meter,
                            h_rx_gnd_meter, pol, f_mhz):
    """Vectorised SAALOS vegetation clutter loss.

    All parameters are broadcast to a common shape.  Scalar inputs produce
    a scalar output value (Python float).  Array inputs produce an ndarray.
    """
    d = np.atleast_1d(np.asarray(d_meter, dtype=np.float64))
    cch = np.atleast_1d(np.asarray(cch_meter, dtype=np.float64))
    htx = np.atleast_1d(np.asarray(h_tx_meter, dtype=np.float64))
    hrx = np.atleast_1d(np.asarray(h_rx_meter, dtype=np.float64))
    hrx_gnd = np.atleast_1d(np.asarray(h_rx_gnd_meter, dtype=np.float64))
    f = np.atleast_1d(np.asarray(f_mhz, dtype=np.float64))
    scalar_out = (
        np.ndim(d_meter) == 0 and np.ndim(cch_meter) == 0
        and np.ndim(h_tx_meter) == 0 and np.ndim(h_rx_meter) == 0
    )
    shape = np.broadcast_shapes(d.shape, cch.shape, htx.shape, hrx.shape,
                                hrx_gnd.shape, f.shape)
    d = np.broadcast_to(d, shape).copy()
    cch = np.broadcast_to(cch, shape).copy()
    htx = np.broadcast_to(htx, shape).copy()
    hrx = np.broadcast_to(hrx, shape).copy()
    hrx_gnd = np.broadcast_to(hrx_gnd, shape).copy()
    f = np.broadcast_to(f, shape).copy()
    pol_arr = np.broadcast_to(np.atleast_1d(np.asarray(pol, dtype=np.int32)), shape)

    result = np.zeros_like(d, dtype=np.float64)

    active = (cch > 0.0) & (d > 0.0) & (hrx < cch)
    if not active.any():
        return result

    wn = np.where(active, f / 47.7, 1.0)
    pd = d
    pdk = pd / 1000.0

    above = active & (htx > cch)
    below = active & ~above

    if above.any():
        _saalos_vec_above(result, above, pd, pdk, cch, htx, hrx, hrx_gnd, pol_arr, wn)

    if below.any():
        _saalos_vec_below(result, below, pd, pdk, cch, htx, hrx, wn)

    np.clip(result, 0.0, MAX_CLUTTER_LOSS, out=result)
    result[~active] = 0.0
    if scalar_out:
        return float(result[0])
    return result


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
    m_cch_h = np.maximum(cch - htx, 1e-10)
    q1 = m_cch_h * (2.06943 - 1.56184 * np.exp(1.0 / m_cch_h))
    q2 = (17.98 - 0.84224 * m_cch_h) * np.exp(-0.00000061 * pd)
    arte = q1 + q2 + 1.34795 * 20.0 * np.log10(pd + 1.0)
    arte -= np.maximum(0.01, np.log10(wn * 47.7) - 2.0) * (hrx / np.maximum(htx, 1e-10))
    result[mask] = arte[mask]