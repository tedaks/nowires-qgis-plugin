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

Batch P2P computation and output helpers.
"""

import logging
import math

import numpy as np
from qgis.core import QgsProcessingException

try:
    from qgis.core import NULL as _QGIS_NULL
except ImportError:
    _QGIS_NULL = None

from NoWires.batch.analysis_params import BatchAnalysisParams
from NoWires.batch.writer import write_batch_marker_layer, write_batch_csv, write_batch_json
from NoWires.constants import DEFAULT_PROFILE_STEP_M, CLIMATE_NAMES, MHZ_TO_HZ
from NoWires.elevation import bearing_deg, haversine_m
from NoWires.fresnel import C_LIGHT, fresnel_profile_analysis
from NoWires.radio import (
    build_pfl,
    itm_p2p_loss,
)
from NoWires.antenna import (
    ANTENNA_PRESET_KEYS,
    antenna_config_from_values,
    antenna_gain_adjustment_db,
)
from NoWires.clutter import compute_terminal_clutter_losses

__all__ = [
    "_feat_attr",
    "compute_batch_links",
    "rank_batch_results",
    "write_batch_marker_layer",
    "write_batch_csv",
    "write_batch_json",
]

logger = logging.getLogger(__name__)

def _compute_single_link(tx_def, rx_def, params: BatchAnalysisParams, wavelength_m):
    rx_lat = rx_def["lat"]
    rx_lon = rx_def["lon"]
    tx_h_eff = tx_def["height"] if tx_def["height"] is not None else params.tx_h
    rx_h_eff = rx_def["height"] if rx_def["height"] is not None else params.rx_h

    from NoWires.radio import ITM_MIN_TERMINAL_HEIGHT_M, ITM_MAX_TERMINAL_HEIGHT_M
    if tx_h_eff < ITM_MIN_TERMINAL_HEIGHT_M or tx_h_eff > ITM_MAX_TERMINAL_HEIGHT_M:
        logger.warning("Feature TX height %.1f m out of range [%.1f, %.1f]; skipping",
                      tx_h_eff, ITM_MIN_TERMINAL_HEIGHT_M, ITM_MAX_TERMINAL_HEIGHT_M)
        return None
    if rx_h_eff < ITM_MIN_TERMINAL_HEIGHT_M or rx_h_eff > ITM_MAX_TERMINAL_HEIGHT_M:
        logger.warning("Feature RX height %.1f m out of range [%.1f, %.1f]; skipping",
                      rx_h_eff, ITM_MIN_TERMINAL_HEIGHT_M, ITM_MAX_TERMINAL_HEIGHT_M)
        return None

    dist_m = haversine_m(tx_def["lat"], tx_def["lon"], rx_lat, rx_lon)
    if dist_m < 1.0:
        return None

    if params.elev is None:
        return None
    profile_points = params.elev.terrain_profile(
        tx_def["lat"], tx_def["lon"], rx_lat, rx_lon,
        step_m=DEFAULT_PROFILE_STEP_M)
    if len(profile_points) < 2:
        return None
    distances = [p[0] for p in profile_points]
    elevations = [p[1] for p in profile_points]
    nan_count = sum(1 for e in elevations if math.isnan(e))
    if nan_count == len(elevations):
        return None
    if nan_count > 0:
        from NoWires.nan_utils import interpolate_nan_elevations
        elevations = interpolate_nan_elevations(np.array(elevations, dtype=np.float64))
        if np.all(np.isnan(elevations)):
            return None
    step_m_val = dist_m / max(len(distances) - 1, 1)
    pfl = build_pfl(elevations, step_m_val)

    itm_result = itm_p2p_loss(
        h_tx__meter=tx_h_eff,
        h_rx__meter=rx_h_eff,
        profile=pfl,
        climate=params.climate,
        N0=params.n0,
        f__mhz=params.f_mhz,
        polarization=params.polarization,
        epsilon=params.epsilon,
        sigma=params.sigma,
        time_pct=params.time_pct,
        location_pct=params.location_pct,
        situation_pct=params.situation_pct,
        k_factor=params.k_factor,
    )

    if itm_result.failed or not math.isfinite(itm_result.loss_db):
        return None

    clutter_context = None
    if params.clutter_enabled or params.bel_enabled:
        from NoWires.clutter.context import build_link_clutter_context
        clutter_context = build_link_clutter_context(
            params=params, dist_m=dist_m, tx_h=tx_h_eff, rx_h=rx_h_eff,
            tx_elev=float(elevations[0]), rx_elev=float(elevations[-1]))

    clutter_losses = compute_terminal_clutter_losses(
        tx_lat=tx_def["lat"], tx_lon=tx_def["lon"],
        rx_lat=rx_lat, rx_lon=rx_lon,
        frequency_mhz=params.f_mhz, enabled=params.clutter_enabled or params.bel_enabled,
        land_cover_grid=params.clutter_grid,
        tx_override=params.tx_clutter_override, rx_override=params.rx_clutter_override,
        context=clutter_context,
    )

    from NoWires.constants import ITM_LOSS_UPPER_BOUND
    total_loss_db = min(itm_result.loss_db, ITM_LOSS_UPPER_BOUND) + clutter_losses.total_with_bel_db

    tx_bearing = bearing_deg(tx_def["lat"], tx_def["lon"], rx_lat, rx_lon)
    rx_bearing = bearing_deg(rx_lat, rx_lon, tx_def["lat"], tx_def["lon"])
    vertical_angle = math.degrees(
        math.atan2(
            (elevations[-1] + rx_h_eff) - (elevations[0] + tx_h_eff),
            max(dist_m, 1.0),
        )
    )

    tx_gain_db = tx_def.get("gain_db")
    tx_gain_eff = tx_gain_db if tx_gain_db is not None else params.tx_gain_default
    rx_gain_db = rx_def.get("gain_db")
    rx_gain_eff = rx_gain_db if rx_gain_db is not None else params.rx_gain_default

    tx_preset_key = tx_def.get("antenna_preset", params.tx_default_preset_key)
    if tx_preset_key not in ANTENNA_PRESET_KEYS:
        tx_preset_key = params.tx_default_preset_key
    tx_preset_idx = ANTENNA_PRESET_KEYS.index(tx_preset_key)
    tx_ant_config = antenna_config_from_values(
        preset=tx_preset_idx,
        azimuth_deg=tx_def.get("azimuth", params.tx_default_az),
        front_back_db=params.tx_front_back_db,
    )
    rx_preset_key = rx_def.get("antenna_preset", params.rx_default_preset_key)
    if rx_preset_key not in ANTENNA_PRESET_KEYS:
        rx_preset_key = params.rx_default_preset_key
    rx_preset_idx = ANTENNA_PRESET_KEYS.index(rx_preset_key)
    rx_ant_config = antenna_config_from_values(
        preset=rx_preset_idx,
        azimuth_deg=rx_def.get("azimuth", params.rx_default_az),
        front_back_db=params.rx_front_back_db,
    )

    tx_ant_adj = antenna_gain_adjustment_db(tx_bearing, vertical_angle, tx_ant_config)
    rx_ant_adj = antenna_gain_adjustment_db(rx_bearing, -vertical_angle, rx_ant_config)
    ant_gain_adj_total = tx_ant_adj + rx_ant_adj

    eirp_eff = params.tx_power + tx_gain_eff - params.cable_loss
    prx_dbm = eirp_eff + rx_gain_eff + ant_gain_adj_total - total_loss_db
    margin_db = prx_dbm - params.rx_sens

    tx_antenna_h = elevations[0] + tx_h_eff
    rx_antenna_h = elevations[-1] + rx_h_eff
    terrain_bulge, los_h, fresnel_r, _, _, _ = fresnel_profile_analysis(
        distances, elevations, tx_antenna_h, rx_antenna_h,
        dist_m, wavelength_m, params.k_factor,
    )
    fresnel_clearance = (los_h - fresnel_r) - terrain_bulge
    clearance_pct = float(
        np.sum(fresnel_clearance > 0) / max(len(fresnel_clearance), 1) * 100
    )

    return {
        "tx_lat": tx_def["lat"],
        "tx_lon": tx_def["lon"],
        "rx_lat": rx_lat,
        "rx_lon": rx_lon,
        "dist_m": dist_m,
        "dist_km": dist_m / 1000.0,
        "itm_loss_db": itm_result.loss_db,
        "total_loss_db": total_loss_db,
        "prx_dbm": prx_dbm,
        "margin_db": margin_db,
        "clearance_pct": clearance_pct,
        "status": "VIABLE" if margin_db >= 0 else "NOT VIABLE",
        "tx_height": tx_h_eff,
        "rx_height": rx_h_eff,
        "climate": CLIMATE_NAMES.get(params.climate, str(params.climate)),
    }

def compute_batch_links(params: BatchAnalysisParams, feedback):
    wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)
    results = []
    count = 0

    total = params.total

    for tx_def in params.candidate_tx:
        for rx_def in params.rx_points:
            if feedback.isCanceled():
                raise QgsProcessingException("Batch analysis cancelled by user.")
            try:
                result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
                if result is not None:
                    results.append(result)
            except Exception as exc:
                logger.warning("Skipping TX(%.5f,%.5f)→RX(%.5f,%.5f): %s",
                              tx_def["lat"], tx_def["lon"], rx_def["lat"], rx_def["lon"], exc)
            count += 1
            if count % 100 == 0 or count == total:
                feedback.setProgress(20 + int(60 * count / max(total, 1)))

    return results

def rank_batch_results(results, rank_by):
    if rank_by == 0:
        results.sort(key=lambda r: (r["margin_db"], r["clearance_pct"]), reverse=True)
    elif rank_by == 1:
        results.sort(key=lambda r: (r["itm_loss_db"], r["margin_db"]))
    else:
        results.sort(key=lambda r: (r["clearance_pct"], r["margin_db"]), reverse=True)
    return results


def _feat_attr(feat, name, default):
    """Return feat.attribute(name) cast to the same type as default.

    If default is None, returns float for numeric values or str for strings.
    Returns default on NULL attribute, missing field, or cast failure.
    Logs a warning when coercion truncates a value or fails entirely.
    """
    try:
        val = feat.attribute(name)
    except (KeyError, IndexError):
        return default
    if val is None or val == _QGIS_NULL:
        return default
    if default is None:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return str(val)
        logger.debug("Attribute '%s': unexpected type %s, using default", name, type(val).__name__)
        return default
    try:
        if isinstance(default, float):
            return float(val)
        if isinstance(default, bool):
            return bool(val)
        if isinstance(default, int):
            coerced = int(float(val))
            if float(val) != coerced and isinstance(val, float):
                logger.warning(
                    "Attribute '%s': value %s truncated to %d for int field",
                    name, val, coerced,
                )
            return coerced
        if isinstance(default, str):
            return str(val)
        return default
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Attribute '%s': cannot coerce value %r to %s (%s), using default %r",
            name, val, type(default).__name__, exc, default,
        )
        return default
