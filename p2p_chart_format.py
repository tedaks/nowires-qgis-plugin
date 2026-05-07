# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
         email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
  *                                                                         *
  *   This program is free software; you can redistribute it and/or modify  *
  *   it under the terms of the GNU General Public License as published by  *
  *   the Free Software Foundation; either version 3 of the License, or     *
  *   (at your option) any later version.                                   *
  *                                                                         *
  ***************************************************************************/


Chart formatting helpers for P2P profile display.

Extracted from p2p_chart.py for modularity.
"""

import numpy as np


__all__ = ["build_obstruction_data", "build_chart_status_text"]


def build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r):
    """Find peak obstruction indices and compute per-point deficit values.

    Returns a list of (index, deficit) tuples for up to 5 highest obstructions.
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
    peaks.sort(key=lambda i: terrain_bulge[i], reverse=True)
    return [
        (idx, d_km[idx], terrain_bulge[idx], los_h[idx], fresnel_r[idx],
         max(0, terrain_bulge[idx] - (los_h[idx] - fresnel_r[idx])))
        for idx in peaks[:5]
    ]


def build_chart_status_text(result, prx_dbm, margin_db):
    """Build the status annotation text for the P2P profile chart.

    Returns a multi-line string for placing in the chart area.
    """
    if margin_db is not None:
        status = "VIABLE" if margin_db >= 0 else "NOT VIABLE"
        status_text = "Loss: {:.1f} dB\nPrx: {:.1f} dBm\nMargin: {:.1f} dB\nStatus: {}".format(
            result.loss_db, prx_dbm, margin_db, status)
    else:
        status_text = "Loss: {:.1f} dB\nPrx: {:.1f} dBm".format(
            result.loss_db, prx_dbm)
    return status_text
