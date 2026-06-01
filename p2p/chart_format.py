# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
         email                : tedaks@gmail.com
 ***************************************************************************/

 Licensed under the MIT License; see the LICENSE file for the full text.


Chart formatting helpers for P2P profile display.

Extracted from p2p_chart.py for modularity.
"""

import numpy as np


__all__ = ["build_obstruction_data", "build_chart_status_text"]


def build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r):
    """Find peak obstruction indices sorted by Fresnel penetration deficit.

    Returns a list of (idx, d_km, terrain_bulge, los_h, fresnel_r, deficit)
    tuples for up to 5 obstructions with the highest deficit, where
    deficit = max(0, terrain_bulge - (los_h - fresnel_r)).
    """
    obstruction_indices = np.where(terrain_bulge > los_h - fresnel_r)[0]
    index_set = set(obstruction_indices)
    peaks = []
    for idx in obstruction_indices:
        is_peak = True
        for offset in [-1, 1]:
            neighbor = idx + offset
            if 0 <= neighbor < len(terrain_bulge) and neighbor in index_set:
                if terrain_bulge[neighbor] > terrain_bulge[idx]:
                    is_peak = False
                    break
                if terrain_bulge[neighbor] == terrain_bulge[idx] and neighbor < idx:
                    is_peak = False
                    break
        if is_peak:
            peaks.append(idx)
    deficit = terrain_bulge - (los_h - fresnel_r)
    peaks.sort(key=lambda i: deficit[i], reverse=True)
    return [
        (idx, d_km[idx], terrain_bulge[idx], los_h[idx], fresnel_r[idx],
         max(0, terrain_bulge[idx] - (los_h[idx] - fresnel_r[idx])))
        for idx in peaks[:5]
    ]


def build_chart_status_text(result, prx_dbm, margin_db, itm_loss_db=None):
    """Build the status annotation text for the P2P profile chart.

    Returns a multi-line string for placing in the chart area.
    """
    loss = itm_loss_db if itm_loss_db is not None else result.loss_db
    if margin_db is not None:
        status = "VIABLE" if margin_db >= 0 else "NOT VIABLE"
        status_text = "Loss: {:.1f} dB\nPrx: {:.1f} dBm\nMargin: {:.1f} dB\nStatus: {}".format(
            loss, prx_dbm, margin_db, status)
    else:
        status_text = "Loss: {:.1f} dB\nPrx: {:.1f} dBm".format(loss, prx_dbm)
    return status_text
