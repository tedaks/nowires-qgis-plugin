# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import math

import numpy as np

from NoWires.clutter._saalos_vec import (
    EARTH_RADIUS,
    _saalos_vec_above,
    _saalos_vec_below,
)
from NoWires.clutter.constants import MAX_CLUTTER_LOSS

# SAALOS polarization convention:
#   1 = Horizontal, 2 = Vertical, 0 = Other/fallback
# A translation function (_saalos_pol) maps from the ITM convention
# (0=H, 1=V) used by the rest of the plugin.


def _saalos_pol(itm_pol):
    """Translate ITM polarization convention to SAALOS convention.

    ITM: 0=Horizontal, 1=Vertical. SAALOS: 1=Horizontal, 2=Vertical.
    """
    if itm_pol == 0:
        return 1  # Horizontal
    if itm_pol == 1:
        return 2  # Vertical
    return 0  # Unknown/fallback


def clutter_loss_saalos(d__meter, cch__meter, h_tx__meter, h_rx__meter,
                        h_rx_gnd__meter, pol, f__mhz):
    if cch__meter <= 0.0:
        return 0.0
    if d__meter == 0.0:
        return 0.0
    if h_rx__meter > cch__meter:
        return 0.0

    pol = _saalos_pol(pol)
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
            ctip = max(-1.0, min(1.0, (hone - cch__meter + hc) / ucrpc))
            tip = math.acos(ctip)
            tic = max(0.0, tip + tde)
            stic = math.sin(tic)
            sta = max(-1.0, min(1.0, (ensa / encca) * stic))
            ttc = math.asin(sta)
            cttc = math.sqrt(1.0 - math.sin(ttc) ** 2)
            crpc = (cch__meter - h_rx__meter) / cttc
            if crpc >= dp:
                crpc = dp - 1.0 / max(dp, 1.0)
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
            arte = 0.0195 * crpc - 20.0 * math.log10(max(tsp, 1e-30))
        elif d1a < 225.0:
            if tvsr > 1000.0:
                q = d1a * (0.03 * math.exp(-0.14 * pdk))
            else:
                q = d1a * (0.07 * math.exp(-0.17 * pdk))
            arte = q + (0.7 * pdk - max(0.01, math.log10(wn * 47.7) - 2.0)) * (h_rx__meter / hone)
        else:
            q = 0.00055 * pdk + math.log10(pdk) * (0.041 - 0.0017 * math.sqrt(hone) + 0.019)
            arte = d1a * q - (18.0 * math.log10(max(rsp, 1e-30))) / math.exp(hone / 37.5)
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
        # Below-canopy path: exp(1/cch - htx) matches ITWOM 3.0 itwom3.0.cpp:410
        # and Rust clutterloss-itm-addon-rust/src/lib.rs:186.
        q1 = (cch__meter - h_tx__meter) * (
            2.06943 - 1.56184 * math.exp(min(1.0 / cch__meter - h_tx__meter, 700.0)))
        q2 = (17.98 - 0.84224 * (cch__meter - h_tx__meter)) * math.exp(-0.00000061 * pd)
        arte = q1 + q2 + 1.34795 * 20.0 * math.log10(pd + 1.0)
        arte -= max(0.01, math.log10(wn * 47.7) - 2.0) * (h_rx__meter / max(h_tx__meter, 1e-10))
        if math.isnan(arte):
            return MAX_CLUTTER_LOSS

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
    pol = _saalos_pol(pol)
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
