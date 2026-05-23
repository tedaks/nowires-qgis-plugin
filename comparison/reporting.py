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


Coverage comparison reporting and validation helpers.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
from qgis.core import QgsProcessingException

from NoWires.constants import CLIMATE_NAMES


def validate_panels(tx_point_a, tx_point_b, radius_km_a, radius_km_b):
    if tx_point_a is None:
        raise QgsProcessingException("Panel A TX point is required.")
    if tx_point_b is None:
        raise QgsProcessingException("Panel B TX point is required.")
    tx_lat_a, tx_lon_a = tx_point_a.y(), tx_point_a.x()
    tx_lat_b, tx_lon_b = tx_point_b.y(), tx_point_b.x()
    if abs(tx_lat_a - tx_lat_b) > 1e-3 or abs(tx_lon_a - tx_lon_b) > 1e-3:
        raise QgsProcessingException(
            "Panel A and B TX positions differ. "
            "Delta comparison requires co-located transmitters.")
    if abs(radius_km_a - radius_km_b) > 1e-6:
        raise QgsProcessingException(
            "Panel A and B radii differ. "
            "Delta comparison requires identical analysis radii.")
    return tx_lat_a, tx_lon_a, tx_lat_b, tx_lon_b


def resolve_output_paths(
    output_dir: str | None,
    out_a: str | None,
    out_b: str | None,
    out_delta: str | None,
    out_report: str | None,
    tmp_mgr: Any,
) -> tuple[str, str, str, str | None, str | None]:
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_a = out_a or os.path.join(output_dir, "coverage_a.tif")
        out_b = out_b or os.path.join(output_dir, "coverage_b.tif")
        out_delta = out_delta or os.path.join(output_dir, "coverage_delta.tif")
        out_report = out_report or os.path.join(output_dir, "comparison_report.html")
    tmpdir: str | None = None
    if not out_a or not out_b or not out_delta:
        tmpdir = tmp_mgr.make_dir("comp", persistent=True)
    if not out_a:
        out_a = os.path.join(tmpdir, "coverage_a.tif")  # type: ignore[arg-type]
    if not out_b:
        out_b = os.path.join(tmpdir, "coverage_b.tif")  # type: ignore[arg-type]
    if not out_delta:
        out_delta = os.path.join(tmpdir, "coverage_delta.tif")  # type: ignore[arg-type]
    return out_a, out_b, out_delta, out_report, tmpdir


def build_panel_info(panel, prx_grid):
    valid_mask = ~np.isnan(prx_grid)
    info = {
        "tx_lat": panel["tx_lat"], "tx_lon": panel["tx_lon"],
        "tx_h": panel["tx_h"], "rx_h": panel["rx_h"],
        "f_mhz": panel["f_mhz"], "radius_km": panel["radius_km"],
        "tx_power": panel["tx_power"], "tx_gain": panel["tx_gain"],
        "rx_gain": panel["rx_gain"], "cable_loss": panel["cable_loss"],
        "climate": CLIMATE_NAMES.get(panel.get("climate"), str(panel.get("climate", ""))),
        "valid_pixels": int(valid_mask.sum()),
        "total_pixels": int(prx_grid.size),
        "mean_prx": float(np.nanmean(prx_grid)) if valid_mask.any() else float("nan"),
    }
    return info


def build_delta_info(delta_style, threshold_db, ds):
    valid_count = ds["valid_count"]
    improved = ds["improved"]
    degraded = ds["degraded"]
    unchanged = ds["unchanged"]
    pct_scale = 100.0 / valid_count if valid_count > 0 else 0.0
    return {
        "style": delta_style,
        "threshold_db": threshold_db,
        "valid_pixels": valid_count,
        "improved_pixels": improved,
        "improved_pct": improved * pct_scale,
        "degraded_pixels": degraded,
        "degraded_pct": degraded * pct_scale,
        "unchanged_pixels": unchanged,
        "unchanged_pct": unchanged * pct_scale,
        "min_delta": ds["min_delta"],
        "max_delta": ds["max_delta"],
        "mean_delta": ds["mean_delta"],
    }


def report_comparison_results(feedback, valid_count, total_count, delta_info, threshold_db):
    feedback.pushInfo("")
    feedback.pushInfo("=" * 50)
    feedback.pushInfo("COVERAGE COMPARISON RESULTS")
    feedback.pushInfo("=" * 50)
    feedback.pushInfo("Valid delta pixels: {} / {}".format(valid_count, total_count))
    feedback.pushInfo("Improved (A better, <-{:.1f} dB): {} ({:.1f}%)".format(
        threshold_db, delta_info["improved_pixels"], delta_info["improved_pct"]))
    feedback.pushInfo("Degraded (A worse, >+{:.1f} dB): {} ({:.1f}%)".format(
        threshold_db, delta_info["degraded_pixels"], delta_info["degraded_pct"]))
    feedback.pushInfo("Unchanged (within threshold): {} ({:.1f}%)".format(
        delta_info["unchanged_pixels"], delta_info["unchanged_pct"]))
    feedback.pushInfo("Delta range: {:.2f} to {:.2f} dB (mean: {:.2f} dB)".format(
        delta_info["min_delta"], delta_info["max_delta"], delta_info["mean_delta"]))
    feedback.pushInfo("=" * 50)
