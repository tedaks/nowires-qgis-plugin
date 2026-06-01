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


Coverage Algorithm — Report building and feedback output.

Extracted from algorithm_coverage.py for modularity.
"""

import numpy as np

from NoWires.clutter import CLUTTER_MODEL_OPTIONS
from NoWires.clutter.context import ClutterModel
from NoWires.antenna import ANTENNA_PRESET_OPTIONS
from NoWires.constants import CLIMATE_NAMES, POLARIZATION_NAMES
from NoWires.radio_coverage.summary import summarize_coverage_grid
from NoWires.report.payloads import (
    build_coverage_report_payload,
    build_empty_coverage_report_payload,
)
from NoWires.raster_io import write_geotiff
from NoWires.radio_coverage.coverage_grids import CoverageGrids
from NoWires.radio_coverage.analysis_params import CoverageAnalysisParams


def _clutter_model_label(enabled, model: ClutterModel = "simple", clutter_source: str = ""):
    if not enabled:
        return CLUTTER_MODEL_OPTIONS[0]
    label = CLUTTER_MODEL_OPTIONS[2] if model == "advanced" else CLUTTER_MODEL_OPTIONS[1]
    if clutter_source == "fallback_open":
        label += " (WorldCover unavailable — clutter skipped)"
    return label


def build_coverage_report_payload_for_grid(
    *,
    grids: CoverageGrids,
    params: CoverageAnalysisParams,
    clutter_source: str = "",
    tx_clutter_for_report=None,
    extra_inputs: dict | None = None,
):
    raster_grid = grids.prx_grid[::-1]
    valid = ~np.isnan(raster_grid)
    if not valid.any():
        return build_empty_coverage_report_payload(
            tx_lat=params.tx_lat, tx_lon=params.tx_lon, tx_h=params.tx_h,
            rx_h=params.rx_h, f_mhz=params.f_mhz, radius_km=params.radius_km,
            grid_size=params.grid_size,
            polarization_name=POLARIZATION_NAMES.get(params.polarization, str(params.polarization)),
            climate_name=CLIMATE_NAMES.get(params.climate, str(params.climate)),
            time_pct=params.time_pct, location_pct=params.location_pct,
            situation_pct=params.situation_pct, tx_power=params.tx_power,
            tx_gain=params.tx_gain, rx_gain=params.rx_gain,
            cable_loss=params.cable_loss,
            rx_sensitivity_dbm=params.rx_sens, pixel_count=int(raster_grid.size),
            clutter_model=_clutter_model_label(params.clutter_enabled, params.clutter_model, clutter_source),
            clutter_source=clutter_source,
            tx_antenna_preset=ANTENNA_PRESET_OPTIONS[params.antenna_preset],
            clutter_tx_db=tx_clutter_for_report.tx_loss_db,
            **(extra_inputs or {}),
        ), raster_grid, valid, None

    pct_above = (
        float((raster_grid[valid] >= params.rx_sens).sum()) / max(valid.sum(), 1) * 100
    )
    summary = summarize_coverage_grid(
        prx_grid=raster_grid, tx_lat=params.tx_lat, tx_lon=params.tx_lon,
        min_lat=grids.min_lat, max_lat=grids.max_lat,
        min_lon=grids.min_lon, max_lon=grids.max_lon,
        rx_sensitivity_dbm=params.rx_sens,
    )
    component_valid = ~np.isnan(grids.loss_grid)
    itm_loss_db = (
        float(np.nanmean(grids.itm_loss_grid[component_valid]))
        if component_valid.any() else None
    )
    total_path_loss_db = (
        float(np.nanmean(grids.loss_grid[component_valid]))
        if component_valid.any() else None
    )
    clutter_rx_db = (
        float(np.nanmean(grids.clutter_rx_db_grid[component_valid]))
        if component_valid.any() else 0.0
    )
    bel_rx_db = (
        float(np.nanmean(grids.bel_rx_db_grid[component_valid]))
        if component_valid.any() else 0.0
    )
    report_payload = build_coverage_report_payload(
        tx_lat=params.tx_lat, tx_lon=params.tx_lon, tx_h=params.tx_h, rx_h=params.rx_h,
        f_mhz=params.f_mhz, radius_km=params.radius_km, grid_size=params.grid_size,
        polarization_name=POLARIZATION_NAMES.get(params.polarization, str(params.polarization)),
        climate_name=CLIMATE_NAMES.get(params.climate, str(params.climate)),
        time_pct=params.time_pct, location_pct=params.location_pct,
        situation_pct=params.situation_pct, tx_power=params.tx_power,
        tx_gain=params.tx_gain, rx_gain=params.rx_gain,
        cable_loss=params.cable_loss,
        rx_sensitivity_dbm=params.rx_sens, valid_pixel_count=int(valid.sum()),
        pixel_count=int(raster_grid.size),
        min_prx_dbm=float(np.nanmin(raster_grid)),
        max_prx_dbm=float(np.nanmax(raster_grid)),
        mean_prx_dbm=float(np.nanmean(raster_grid)),
        pct_above_sensitivity=pct_above,
        usable_cell_count=int(summary["usable_cell_count"]),
        min_distance_km=summary["min_distance_km"],
        max_distance_km=summary["max_distance_km"],
        average_distance_km=summary["average_distance_km"],
        clutter_model=_clutter_model_label(params.clutter_enabled, params.clutter_model, clutter_source),
        clutter_source=clutter_source,
        tx_antenna_preset=ANTENNA_PRESET_OPTIONS[params.antenna_preset],
        itm_loss_db=itm_loss_db,
        clutter_tx_db=tx_clutter_for_report.tx_loss_db,
        clutter_rx_db=clutter_rx_db,
        bel_rx_db=bel_rx_db,
        total_path_loss_db=total_path_loss_db,
        **(extra_inputs or {}),
    )
    return report_payload, raster_grid, valid, summary


def report_coverage_results(feedback, report_payload, raster_grid, valid, rx_sens, summary=None):
    """Log coverage results to the processing feedback.

    Reads precomputed statistics from *report_payload* (already calculated
    by :func:`build_coverage_report_payload_for_grid`) to avoid redundant
    numpy scans over large grids.
    """
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
        results = report_payload.get("results", {})
        min_prx = results.get("min_prx_dbm", float("nan"))
        max_prx = results.get("max_prx_dbm", float("nan"))
        mean_prx = results.get("mean_prx_dbm", float("nan"))
        pct_above = results.get("pct_above_sensitivity", 0.0)
        feedback.pushInfo(
            "Min Prx: {:.1f} dBm".format(min_prx)
        )
        feedback.pushInfo(
            "Max Prx: {:.1f} dBm".format(max_prx)
        )
        feedback.pushInfo(
            "Mean Prx: {:.1f} dBm".format(mean_prx)
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
