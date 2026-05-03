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


Pure-Python helpers for NoWires report payloads.
"""

from __future__ import annotations

from .reliability import summarize_reliability


def build_p2p_report_payload(
    tx_lat, tx_lon, rx_lat, rx_lon, tx_h, rx_h, f_mhz,
    polarization_name, climate_name, k_factor, dist_m, propagation_mode,
    propagation_mode_name, fspl_db, itm_loss_db, tx_power, tx_gain, rx_gain,
    cable_loss, eirp_dbm, prx_dbm, rx_sensitivity_dbm, margin_db, los_blocked,
    fresnel_1_violated, fresnel_60_violated, max_fresnel_radius_m,
    total_path_loss_db=None, clutter_tx_db=0.0, clutter_rx_db=0.0,
    clutter_source="off", tx_antenna_preset="omni", rx_antenna_preset="omni",
    antenna_gain_adjustment_db=0.0,
):
    """Build the structured P2P report payload."""
    reliability = summarize_reliability(
        margin_db=margin_db, frequency_mhz=f_mhz,
        distance_km=dist_m / 1000.0, los_blocked=los_blocked,
    )
    return {
        "report_type": "p2p",
        "generated_by": "NoWires",
        "inputs": {
            "tx_lat": round(tx_lat, 6), "tx_lon": round(tx_lon, 6),
            "rx_lat": round(rx_lat, 6), "rx_lon": round(rx_lon, 6),
            "tx_height_m": tx_h, "rx_height_m": rx_h,
            "frequency_mhz": f_mhz, "polarization": polarization_name,
            "climate": climate_name, "k_factor": round(k_factor, 6),
            "tx_power_dbm": tx_power, "tx_gain_dbi": tx_gain,
            "rx_gain_dbi": rx_gain, "cable_loss_db": cable_loss,
            "rx_sensitivity_dbm": rx_sensitivity_dbm,
            "tx_antenna_preset": tx_antenna_preset,
            "rx_antenna_preset": rx_antenna_preset,
            "clutter_source": clutter_source,
        },
        "results": {
            "distance_m": dist_m,
            "distance_km": round(dist_m / 1000.0, 3),
            "propagation_mode": propagation_mode,
            "propagation_mode_name": propagation_mode_name,
            "free_space_loss_db": fspl_db, "itm_path_loss_db": itm_loss_db,
            "excess_loss_db": itm_loss_db - fspl_db, "eirp_dbm": eirp_dbm,
            "clutter_tx_db": clutter_tx_db, "clutter_rx_db": clutter_rx_db,
            "total_path_loss_db": (
                itm_loss_db if total_path_loss_db is None else total_path_loss_db
            ),
            "antenna_gain_adjustment_db": antenna_gain_adjustment_db,
            "received_power_dbm": prx_dbm, "link_margin_db": margin_db,
            "availability_method": reliability["availability_method"],
            "availability_estimate_pct": reliability["availability_estimate_pct"],
            "fade_margin_class": reliability["fade_margin_class"],
            "reliability_summary": reliability["reliability_summary"],
            "los_blocked": bool(los_blocked),
            "fresnel_1_violated": bool(fresnel_1_violated),
            "fresnel_60_violated": bool(fresnel_60_violated),
            "max_fresnel_radius_m": max_fresnel_radius_m,
        },
        "status": {
            "summary": "VIABLE" if margin_db >= 0 else "NOT VIABLE",
            "viable": bool(margin_db >= 0),
        },
    }


def _build_coverage_input_dict(**kw):
    """Build the shared "inputs" section for coverage report payloads."""
    return {
        "tx_lat": round(kw["tx_lat"], 6),
        "tx_lon": round(kw["tx_lon"], 6),
        "tx_height_m": kw["tx_h"], "rx_height_m": kw["rx_h"],
        "frequency_mhz": kw["f_mhz"],
        "max_analysis_distance_km": kw["radius_km"], "grid_size": kw["grid_size"],
        "polarization": kw["polarization_name"], "climate": kw["climate_name"],
        "time_pct": kw["time_pct"], "location_pct": kw["location_pct"],
        "situation_pct": kw["situation_pct"],
        "tx_power_dbm": kw["tx_power"], "tx_gain_dbi": kw["tx_gain"],
        "rx_gain_dbi": kw["rx_gain"], "cable_loss_db": kw["cable_loss"],
        "rx_sensitivity_dbm": kw["rx_sensitivity_dbm"],
        "clutter_model": kw["clutter_model"],
        "clutter_source": kw["clutter_source"],
        "tx_antenna_preset": kw["tx_antenna_preset"],
    }


def _build_coverage_reliability_results(reliability, itm_loss_db, clutter_tx_db,
                                         clutter_rx_db, total_path_loss_db, extra):
    """Build the shared "results" base for coverage report payloads."""
    results = {
        "itm_loss_db": itm_loss_db, "clutter_tx_db": clutter_tx_db,
        "clutter_rx_db": clutter_rx_db, "total_path_loss_db": total_path_loss_db,
        "availability_method": reliability["availability_method"],
        "availability_estimate_pct": reliability["availability_estimate_pct"],
        "fade_margin_class": reliability["fade_margin_class"],
        "reliability_summary": reliability["reliability_summary"],
    }
    results.update(extra)
    return results


def build_coverage_report_payload(
    tx_lat, tx_lon, tx_h, rx_h, f_mhz, radius_km, grid_size,
    polarization_name, climate_name, time_pct, location_pct, situation_pct,
    tx_power, tx_gain, rx_gain, cable_loss, rx_sensitivity_dbm,
    valid_pixel_count, pixel_count, min_prx_dbm, max_prx_dbm, mean_prx_dbm,
    pct_above_sensitivity, usable_cell_count, min_distance_km, max_distance_km,
    average_distance_km, clutter_model="Off", clutter_source="off",
    tx_antenna_preset="omni", itm_loss_db=None, clutter_tx_db=0.0,
    clutter_rx_db=0.0, total_path_loss_db=None,
):
    """Build the structured coverage report payload."""
    reliability = summarize_reliability(
        margin_db=mean_prx_dbm - rx_sensitivity_dbm, frequency_mhz=f_mhz,
        distance_km=max_distance_km, los_blocked=False,
    )
    inputs = _build_coverage_input_dict(
        tx_lat=tx_lat, tx_lon=tx_lon, tx_h=tx_h, rx_h=rx_h, f_mhz=f_mhz,
        radius_km=radius_km, grid_size=grid_size,
        polarization_name=polarization_name, climate_name=climate_name,
        time_pct=time_pct, location_pct=location_pct, situation_pct=situation_pct,
        tx_power=tx_power, tx_gain=tx_gain, rx_gain=rx_gain,
        cable_loss=cable_loss, rx_sensitivity_dbm=rx_sensitivity_dbm,
        clutter_model=clutter_model, clutter_source=clutter_source,
        tx_antenna_preset=tx_antenna_preset,
    )
    results = _build_coverage_reliability_results(
        reliability, itm_loss_db, clutter_tx_db, clutter_rx_db,
        total_path_loss_db,
        {
            "valid_pixel_count": valid_pixel_count, "pixel_count": pixel_count,
            "min_prx_dbm": min_prx_dbm, "max_prx_dbm": max_prx_dbm,
            "mean_prx_dbm": mean_prx_dbm,
            "pct_above_sensitivity": pct_above_sensitivity,
            "usable_cell_count": usable_cell_count,
            "min_distance_km": min_distance_km, "max_distance_km": max_distance_km,
            "average_distance_km": average_distance_km,
        },
    )
    return {
        "report_type": "coverage", "generated_by": "NoWires",
        "inputs": inputs, "results": results,
        "status": {
            "summary": "HAS USABLE CELLS" if usable_cell_count else "NO USABLE CELLS",
            "usable_cells_present": bool(usable_cell_count),
        },
    }


def build_empty_coverage_report_payload(
    tx_lat, tx_lon, tx_h, rx_h, f_mhz, radius_km, grid_size,
    polarization_name, climate_name, time_pct, location_pct, situation_pct,
    tx_power, tx_gain, rx_gain, cable_loss, rx_sensitivity_dbm, pixel_count,
    clutter_model="Off", clutter_source="off", tx_antenna_preset="omni",
    itm_loss_db=None, clutter_tx_db=0.0, clutter_rx_db=0.0,
    total_path_loss_db=None,
):
    """Build a coverage report payload for a grid with no valid modelled cells."""
    reliability = summarize_reliability(
        margin_db=-999.0, frequency_mhz=f_mhz, distance_km=0.0, los_blocked=False,
    )
    inputs = _build_coverage_input_dict(
        tx_lat=tx_lat, tx_lon=tx_lon, tx_h=tx_h, rx_h=rx_h, f_mhz=f_mhz,
        radius_km=radius_km, grid_size=grid_size,
        polarization_name=polarization_name, climate_name=climate_name,
        time_pct=time_pct, location_pct=location_pct, situation_pct=situation_pct,
        tx_power=tx_power, tx_gain=tx_gain, rx_gain=rx_gain,
        cable_loss=cable_loss, rx_sensitivity_dbm=rx_sensitivity_dbm,
        clutter_model=clutter_model, clutter_source=clutter_source,
        tx_antenna_preset=tx_antenna_preset,
    )
    results = _build_coverage_reliability_results(
        reliability, itm_loss_db, clutter_tx_db, clutter_rx_db,
        total_path_loss_db,
        {
            "valid_pixel_count": 0, "pixel_count": pixel_count,
            "min_prx_dbm": None, "max_prx_dbm": None, "mean_prx_dbm": None,
            "pct_above_sensitivity": 0.0, "usable_cell_count": 0,
            "min_distance_km": 0.0, "max_distance_km": 0.0,
            "average_distance_km": 0.0,
        },
    )
    return {
        "report_type": "coverage", "generated_by": "NoWires",
        "inputs": inputs, "results": results,
        "status": {
            "summary": "NO VALID COVERAGE CELLS", "usable_cells_present": False,
        },
    }