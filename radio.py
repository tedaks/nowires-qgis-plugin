# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 by Bortre Tenamo
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


ITM (Irregular Terrain Model) bridge, signal level definitions,
and Fresnel zone analysis.

Provides ITM calculations via the bundled itm package (from tedaks/pyitm),
signal strength thresholds/colors, and Fresnel zone computations for P2P
link analysis.
The itm package is bundled directly inside this plugin — no external
pip install is required.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import logging
import math

logger = logging.getLogger(__name__)

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

# --- Signal Level Definitions ---

SIGNAL_LEVELS: List[Tuple[float, Tuple[int, int, int, int], str]] = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    (-120.0, (200, 40, 40, 0), "No service"),
]

THRESHOLDS = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
COLORS = np.array(
    [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
)

PROP_MODE_NAMES = {
    1: "Line-of-Sight",
    2: "Diffraction",
    3: "Troposcatter",
}

CLIMATE_NAMES = {
    0: "Equatorial",
    1: "Continental Subtropical",
    2: "Maritime Subtropical",
    3: "Desert",
    4: "Continental Temperate",
    5: "Maritime Temperate (land)",
    6: "Maritime Temperate (sea)",
}


# --- Constants ---

C_LIGHT = 299792458.0  # Speed of light in m/s
EARTH_RADIUS_M = 6371000.0


# --- ITM Bridge ---


@dataclass
class ITMResult:
    loss_db: float
    mode: int
    warnings: int
    d_hzn_tx_m: float = 0.0
    d_hzn_rx_m: float = 0.0
    theta_hzn_tx: float = 0.0
    theta_hzn_rx: float = 0.0
    h_e_tx_m: float = 0.0
    h_e_rx_m: float = 0.0
    N_s: float = 0.0
    delta_h_m: float = 0.0
    A_ref_db: float = 0.0
    A_fs_db: float = 0.0
    d_km: float = 0.0


def _get_itm():
    """Import from the bundled itm package (tedaks/pyitm)."""
    from .itm import Climate, Polarization, TerrainProfile, predict_p2p

    return Climate, Polarization, TerrainProfile, predict_p2p


def build_pfl(elevations, step_m):
    """Build a PFL (profile format list) from elevations and step distance."""
    n = len(elevations) - 1
    if isinstance(elevations, np.ndarray):
        return [float(n), float(step_m)] + elevations.tolist()
    return [float(n), float(step_m)] + [float(x) for x in elevations]


def itm_p2p_loss(
    h_tx__meter,
    h_rx__meter,
    profile,
    climate=1,
    N0=301.0,
    f__mhz=300.0,
    polarization=0,
    epsilon=15.0,
    sigma=0.005,
    mdvar=0,
    time_pct=50.0,
    location_pct=50.0,
    situation_pct=50.0,
):
    """Compute ITM point-to-point basic transmission loss.

    Uses the bundled itm package from tedaks/pyitm.

    Args:
        h_tx__meter: TX antenna height above ground (m).
        h_rx__meter: RX antenna height above ground (m).
        profile: PFL format terrain profile.
        climate: Climate zone (0-6).
        N0: Surface refractivity (N-units).
        f__mhz: Frequency in MHz.
        polarization: 0=horizontal, 1=vertical.
        epsilon: Earth permittivity.
        sigma: Earth conductivity.
        mdvar: Mode of variability.
        time_pct: Time percentage.
        location_pct: Location percentage.
        situation_pct: Situation percentage.

    Returns:
        ITMResult dataclass.
    """
    Climate, Polarization, TerrainProfile, predict_p2p = _get_itm()

    terrain = TerrainProfile.from_pfl(profile)
    climate_enum = Climate(int(climate) + 1)
    pol_enum = Polarization(int(polarization))

    try:
        result = predict_p2p(
            h_tx__meter=h_tx__meter,
            h_rx__meter=h_rx__meter,
            terrain=terrain,
            climate=climate_enum,
            N_0=N0,
            f__mhz=f__mhz,
            pol=pol_enum,
            epsilon=epsilon,
            sigma=sigma,
            mdvar=int(mdvar),
            time=time_pct,
            location=location_pct,
            situation=situation_pct,
            return_intermediate=True,
        )
    except (ValueError, RuntimeError, FloatingPointError):
        return ITMResult(loss_db=999.0, mode=0, warnings=1)

    inter = result.intermediate
    mode = 0
    if inter is not None:
        mode_val = inter.mode
        if mode_val is not None and not (
            isinstance(mode_val, float) and mode_val != mode_val
        ):
            mode = int(mode_val)

    warnings_val = int(result.warnings)

    if inter is not None:
        return ITMResult(
            loss_db=result.A__db,
            mode=mode,
            warnings=warnings_val,
            d_hzn_tx_m=inter.d_hzn__meter[0],
            d_hzn_rx_m=inter.d_hzn__meter[1],
            theta_hzn_tx=inter.theta_hzn[0],
            theta_hzn_rx=inter.theta_hzn[1],
            h_e_tx_m=inter.h_e__meter[0],
            h_e_rx_m=inter.h_e__meter[1],
            N_s=inter.N_s,
            delta_h_m=inter.delta_h__meter,
            A_ref_db=inter.A_ref__db,
            A_fs_db=inter.A_fs__db,
            d_km=inter.d__km,
        )

    return ITMResult(loss_db=result.A__db, mode=mode, warnings=warnings_val)


# --- Fresnel Zone Analysis ---


def fresnel_radius(d1_m, d2_m, f_mhz):
    """Compute first Fresnel zone radius at a point along the path."""
    if d1_m <= 0 or d2_m <= 0:
        return 0.0
    wavelength_m = C_LIGHT / (f_mhz * 1e6)
    return math.sqrt(wavelength_m * d1_m * d2_m / (d1_m + d2_m))


def earth_bulge(d_m, total_dist_m, k_factor=4.0 / 3.0):
    """Compute earth curvature bulge at distance d along a path."""
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
    violates_f60 = terrain_bulge > (los_h - 0.6 * fr)

    return terrain_bulge, los_h, fr, obstructs_los, violates_f1, violates_f60


def interpolate_nans(values):
    """Replace NaN values with linear interpolation from neighbours.

    Vectorized using numpy for O(n) instead of O(n^2).
    """
    if not values:
        return values
    arr = np.asarray(values, dtype=np.float64)
    nans = np.isnan(arr)
    if not nans.any():
        return arr.tolist()
    valid = ~nans
    if not valid.any():
        return arr.tolist()
    arr[nans] = np.interp(np.where(nans)[0], np.where(valid)[0], arr[valid])
    return arr.tolist()
