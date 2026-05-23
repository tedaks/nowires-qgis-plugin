# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
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

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

Fresnel zone analysis and earth-bulge calculations for P2P link profiling.

Provides first-Fresnel-zone radius, earth curvature bulge, and full profile
analysis (Fresnel clearance, LOS obstruction, 60% clearance checks).
"""

import math

import numpy as np

from NoWires.constants import EARTH_RADIUS_M
from NoWires.constants import FRESNEL_60PCT_FACTOR

C_LIGHT = 299792458.0


def fresnel_radius(d1_m, d2_m, f_mhz):
    """Compute first Fresnel zone radius at a point along the path."""
    if f_mhz <= 0:
        return 0.0
    if d1_m <= 0 or d2_m <= 0:
        return 0.0
    wavelength_m = C_LIGHT / (f_mhz * 1e6)
    return math.sqrt(wavelength_m * d1_m * d2_m / (d1_m + d2_m))


def earth_bulge(d_m, total_dist_m, k_factor=4.0 / 3.0):
    """Compute earth curvature bulge at distance d along a path."""
    if k_factor <= 0:
        return 0.0
    a_eff = k_factor * EARTH_RADIUS_M
    return (d_m * (total_dist_m - d_m)) / (2.0 * a_eff)


def fresnel_profile_analysis(
    distances,
    elevations,
    tx_antenna_h,
    rx_antenna_h,
    dist_m,
    wavelength_m,
    k_factor=4.0 / 3.0,
):
    """Fresnel/earth-bulge/LOS analysis over a terrain profile.

    Pure numpy implementation (numba-free) for QGIS compatibility.

    Args:
        distances: Array of distances along path (m).
        elevations: Array of terrain elevations (m).
        tx_antenna_h: TX antenna absolute height (m AMSL).
        rx_antenna_h: RX antenna absolute height (m AMSL).
        dist_m: Total path distance (m).
        wavelength_m: Wavelength in metres.
        k_factor: Effective earth radius factor.

    Returns:
        Tuple of (terrain_bulge, los_h, fresnel_r, obstructs_los,
                  violates_f1, violates_f60) arrays.
    """
    if k_factor <= 0:
        n = len(distances) if hasattr(distances, '__len__') else 1
        z = np.zeros(n, dtype=np.float64)
        zb = np.zeros(n, dtype=bool)
        return z.copy(), z.copy(), z.copy(), zb.copy(), zb.copy(), zb.copy()
    if dist_m <= 0:
        raise ValueError(
            "fresnel_profile_analysis requires dist_m > 0, got {}".format(dist_m)
        )
    a_eff = k_factor * EARTH_RADIUS_M

    d = np.asarray(distances, dtype=np.float64)
    e = np.asarray(elevations, dtype=np.float64)

    t = np.divide(d, dist_m, out=np.zeros_like(d), where=dist_m > 0)
    bulge = (d * (dist_m - d)) / (2.0 * a_eff)
    terrain_bulge = e + bulge
    los_h = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)

    d2 = dist_m - d
    with np.errstate(divide="ignore", invalid="ignore"):
        fr = np.sqrt(
            np.where((d > 0) & (d2 > 0), wavelength_m * d * d2 / (d + d2), 0.0)
        )

    obstructs_los = terrain_bulge > los_h
    violates_f1 = terrain_bulge > (los_h - fr)
    violates_f60 = terrain_bulge > (los_h - FRESNEL_60PCT_FACTOR * fr)

    return terrain_bulge, los_h, fr, obstructs_los, violates_f1, violates_f60
