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

ITM (Irregular Terrain Model) bridge and signal level definitions.

Provides ITM calculations via the bundled itm package (from tedaks/pyitm)
and signal strength thresholds/colors for P2P link analysis.
The itm package is bundled directly inside this plugin — no external
pip install is required.

Fresnel zone and earth-bulge functions live in the sibling fresnel module.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import logging
import math

logger = logging.getLogger(__name__)

from dataclasses import dataclass

import numpy as np

from NoWires.defaults import (
    DEFAULT_EPSILON, DEFAULT_FREQ_MHZ, DEFAULT_K_FACTOR, DEFAULT_N0, DEFAULT_SIGMA,
)


# --- Signal Level Definitions ---

from NoWires.constants import SIGNAL_LEVELS

THRESHOLDS = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
COLORS = np.array(
    [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
)

PROP_MODE_NAMES = {
    1: "Line-of-Sight",
    2: "Diffraction",
    3: "Troposcatter",
}


# --- Constants ---

# Earth-radius factor (k) presets exposed by the P2P algorithm UI.
# Index 2 (4/3) is the standard-atmosphere default.
K_FACTOR_PRESETS = [0.67, 1.0, DEFAULT_K_FACTOR, 2.0, 4.0]
ITM_MIN_TERMINAL_HEIGHT_M = 0.5
ITM_MAX_TERMINAL_HEIGHT_M = 3000.0
ITM_MIN_FREQUENCY_MHZ = 20.0
ITM_MAX_FREQUENCY_MHZ = 20000.0
ITM_MIN_N0 = 250.0
ITM_MAX_N0 = 400.0
ITM_MIN_SIGMA = 1e-6
ITM_MIN_CLIMATE = 0
ITM_MAX_CLIMATE = 6


def resolve_k_factor(
    has_preset, has_custom, custom_value, preset_index, presets=K_FACTOR_PRESETS
):
    """Pick the effective Earth-radius factor (k) for a P2P run.

    Prefers the preset enum; falls back to the legacy numeric K_FACTOR only
    when the preset is absent and the custom value was supplied.
    """
    if has_preset and has_custom:
        logger.warning(
            "K_FACTOR preset selected; custom K_FACTOR=%s is ignored, "
            "using preset index %s instead.",
            custom_value, preset_index,
        )
    if not has_preset and has_custom:
        return float(custom_value)
    return presets[preset_index]


def validate_itm_input_ranges(
    tx_height_m,
    rx_height_m,
    frequency_mhz,
    surface_refractivity_n0,
    earth_conductivity_sigma,
    climate=0,
):
    """Validate user inputs against the bundled ITM model's hard limits."""
    checks = [
        (
            "TX antenna height",
            tx_height_m,
            ITM_MIN_TERMINAL_HEIGHT_M,
            ITM_MAX_TERMINAL_HEIGHT_M,
            "m",
        ),
        (
            "RX antenna height",
            rx_height_m,
            ITM_MIN_TERMINAL_HEIGHT_M,
            ITM_MAX_TERMINAL_HEIGHT_M,
            "m",
        ),
        (
            "Frequency",
            frequency_mhz,
            ITM_MIN_FREQUENCY_MHZ,
            ITM_MAX_FREQUENCY_MHZ,
            "MHz",
        ),
        (
            "Surface refractivity N0",
            surface_refractivity_n0,
            ITM_MIN_N0,
            ITM_MAX_N0,
            "N-units",
        ),
        (
            "Climate zone",
            climate,
            ITM_MIN_CLIMATE,
            ITM_MAX_CLIMATE,
            "",
        ),
    ]
    for label, value, min_value, max_value, unit in checks:
        if value < min_value or value > max_value:
            raise ValueError(
                "{} must be between {} and {} {}.".format(
                    label, min_value, max_value, unit
                )
            )

    if earth_conductivity_sigma < ITM_MIN_SIGMA:
        raise ValueError(
            "Earth conductivity sigma must be at least {} S/m.".format(
                ITM_MIN_SIGMA
            )
        )


# --- ITM Bridge ---


@dataclass
class ITMResult:
    loss_db: float
    mode: int
    warnings: int
    failed: bool = False
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
    from NoWires.itm import Climate, Polarization, TerrainProfile, predict_p2p

    return Climate, Polarization, TerrainProfile, predict_p2p


def build_pfl(elevations, step_m):
    """Build a PFL (profile format list) from elevations and step distance."""
    n = max(len(elevations) - 1, 1)
    return [float(n), float(step_m)] + [float(x) for x in elevations]


def itm_p2p_loss(
    h_tx__meter,
    h_rx__meter,
    profile,
    climate=1,
    N0=DEFAULT_N0,
    f__mhz=DEFAULT_FREQ_MHZ,
    polarization=0,
    epsilon=DEFAULT_EPSILON,
    sigma=DEFAULT_SIGMA,
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
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        logger.warning("ITM call failed: %s", exc, exc_info=True)
        return ITMResult(loss_db=float('nan'), mode=-1, warnings=1, failed=True)

    inter = result.intermediate
    mode = 0
    if inter is not None:
        mode_val = inter.mode
        if mode_val is not None and not (
            isinstance(mode_val, float) and math.isnan(mode_val)
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


