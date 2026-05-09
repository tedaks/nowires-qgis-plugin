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


Coverage Algorithm — Report building and feedback output.

Extracted from algorithm_coverage.py for modularity.
"""

import numpy as np

from .clutter import CLUTTER_MODEL_OPTIONS
from .antenna import ANTENNA_PRESET_OPTIONS
from .constants import CLIMATE_NAMES, POLARIZATION_NAMES
from .coverage_summary import summarize_coverage_grid
from .report_payloads import (
    build_coverage_report_payload,
    build_empty_coverage_report_payload,
)
from .raster_io import write_geotiff


def _clutter_model_label(enabled, model="simple"):
    if not enabled:
        return CLUTTER_MODEL_OPTIONS[0]
    return CLUTTER_MODEL_OPTIONS[2] if model == "advanced" else CLUTTER_MODEL_OPTIONS[1]


def build_coverage_report_payload_for_grid(
    prx_grid,
    loss_grid,
    itm_loss_grid,
    clutter_loss_grid,
    min_lat,
    max_lat,
    min_lon,
    max_lon,
    *,
    tx_lat,
    tx_lon,
    tx_h,
    rx_h,
    f_mhz,
    radius_km,
    grid_size,
    polarization,
    climate,
    time_pct,
    location_pct,
    situation_pct,
    tx_power,
    tx_gain,
    rx_gain,
    cable_loss,
    rx_sens,
    clutter_enabled,
    clutter_source,
    antenna_preset,
    tx_clutter_for_report,
    clutter_model="simple",
):
    raster_grid = prx_grid[::-1]
    valid = ~np.isnan(raster_grid)
    if not valid.any():
        return build_empty_coverage_report_payload(
            tx_lat=tx_lat, tx_lon=tx_lon, tx_h=tx_h, rx_h=rx_h,
            f_mhz=f_mhz, radius_km=radius_km, grid_size=grid_size,
            polarization_name=POLARIZATION_NAMES.get(polarization, str(polarization)),
            climate_name=CLIMATE_NAMES.get(climate, str(climate)),
            time_pct=time_pct, location_pct=location_pct,
            situation_pct=situation_pct, tx_power=tx_power, tx_gain=tx_gain,
            rx_gain=rx_gain, cable_loss=cable_loss,
            rx_sensitivity_dbm=rx_sens, pixel_count=int(raster_grid.size),
            clutter_model=_clutter_model_label(clutter_enabled, clutter_model),
            clutter_source=clutter_source,
            tx_antenna_preset=ANTENNA_PRESET_OPTIONS[antenna_preset],
            clutter_tx_db=tx_clutter_for_report.tx_loss_db,
        ), raster_grid, valid, None

    pct_above = (
        float((raster_grid[valid] >= rx_sens).sum()) / max(valid.sum(), 1) * 100
    )
    summary = summarize_coverage_grid(
        prx_grid=raster_grid, tx_lat=tx_lat, tx_lon=tx_lon,
        min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon,
        rx_sensitivity_dbm=rx_sens,
    )
    component_valid = ~np.isnan(loss_grid)
    itm_loss_db = (
        float(np.nanmean(itm_loss_grid[component_valid]))
        if component_valid.any() else None
    )
    total_path_loss_db = (
        float(np.nanmean(loss_grid[component_valid]))
        if component_valid.any() else None
    )
    clutter_total_db = (
        float(np.nanmean(clutter_loss_grid[component_valid]))
        if component_valid.any() else 0.0
    )
    clutter_rx_db = max(0.0, clutter_total_db - tx_clutter_for_report.tx_loss_db)
    report_payload = build_coverage_report_payload(
        tx_lat=tx_lat, tx_lon=tx_lon, tx_h=tx_h, rx_h=rx_h,
        f_mhz=f_mhz, radius_km=radius_km, grid_size=grid_size,
        polarization_name=POLARIZATION_NAMES.get(polarization, str(polarization)),
        climate_name=CLIMATE_NAMES.get(climate, str(climate)),
        time_pct=time_pct, location_pct=location_pct,
        situation_pct=situation_pct, tx_power=tx_power, tx_gain=tx_gain,
        rx_gain=rx_gain, cable_loss=cable_loss,
        rx_sensitivity_dbm=rx_sens, valid_pixel_count=int(valid.sum()),
        pixel_count=int(raster_grid.size),
        min_prx_dbm=float(np.nanmin(raster_grid)),
        max_prx_dbm=float(np.nanmax(raster_grid)),
        mean_prx_dbm=float(np.nanmean(raster_grid)),
        pct_above_sensitivity=pct_above,
        usable_cell_count=int(summary["usable_cell_count"]),
        min_distance_km=summary["min_distance_km"],
        max_distance_km=summary["max_distance_km"],
        average_distance_km=summary["average_distance_km"],
        clutter_model=_clutter_model_label(clutter_enabled, clutter_model),
        clutter_source=clutter_source,
        tx_antenna_preset=ANTENNA_PRESET_OPTIONS[antenna_preset],
        itm_loss_db=itm_loss_db,
        clutter_tx_db=tx_clutter_for_report.tx_loss_db,
        clutter_rx_db=clutter_rx_db,
        total_path_loss_db=total_path_loss_db,
    )
    return report_payload, raster_grid, valid, summary


def report_coverage_results(feedback, report_payload, raster_grid, valid, rx_sens, summary=None):
    feedback.pushInfo("")
    feedback.pushInfo("=" * 40)
    feedback.pushInfo("COVERAGE RESULTS")
    feedback.pushInfo("=" * 40)
    feedback.pushInfo(
        "Valid pixels: {} / {}".format(int(valid.sum()), raster_grid.size)
    )
    if not valid.any():
        feedback.pushInfo("No valid coverage cells were computed.")
    else:
        feedback.pushInfo(
            "Min Prx: {:.1f} dBm".format(float(np.nanmin(raster_grid)))
        )
        feedback.pushInfo(
            "Max Prx: {:.1f} dBm".format(float(np.nanmax(raster_grid)))
        )
        feedback.pushInfo(
            "Mean Prx: {:.1f} dBm".format(float(np.nanmean(raster_grid)))
        )
        pct_above = (
            float((raster_grid[valid] >= rx_sens).sum()) / max(valid.sum(), 1) * 100
        )
        feedback.pushInfo(
            "Above sensitivity ({:.0f} dBm): {:.1f}%".format(rx_sens, pct_above)
        )
        if summary is not None:
            feedback.pushInfo(
                "Min usable distance: {:.2f} km".format(summary["min_distance_km"])
            )
            feedback.pushInfo(
                "Max usable distance: {:.2f} km".format(summary["max_distance_km"])
            )
            feedback.pushInfo(
                "Average usable distance: {:.2f} km".format(
                    summary["average_distance_km"]
                )
            )
    feedback.pushInfo(
        "Availability method: {}".format(
            report_payload["results"]["availability_method"]
        )
    )
    feedback.pushInfo(
        "Reliability: {}".format(
            report_payload["results"]["reliability_summary"]
        )
    )
    feedback.pushInfo(
        "Fade margin class: {}".format(
            report_payload["results"]["fade_margin_class"]
        )
    )
    if report_payload["results"]["availability_estimate_pct"] is not None:
        feedback.pushInfo(
            "Availability estimate: {:.2f}%".format(
                report_payload["results"]["availability_estimate_pct"]
            )
        )
    if valid.any() and summary is not None and summary["usable_cell_count"] == 0:
        feedback.pushInfo("No cells met the RX sensitivity threshold.")
    feedback.pushInfo("=" * 40)


def write_coverage_geotiff(prx_grid, min_lat, max_lat, min_lon, max_lon, tif_path):
    write_geotiff(tif_path, prx_grid, min_lat, max_lat, min_lon, max_lon)
