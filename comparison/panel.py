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


Coverage Comparison Algorithm — Panel coverage runner.

Standalone function to run compute_coverage for one panel of the comparison.
"""

from NoWires.coverage.compute import (
    DEFAULT_MAX_PROFILE_PTS,
    coverage_profile_step_m,
)
from NoWires.coverage.engine import compute_coverage
from NoWires.clutter import (
    LandCoverGrid,
    clutter_source_label,
    compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area,
)
from qgis.core import QgsProcessingException
from NoWires.radio import validate_itm_input_ranges
from NoWires.comparison.params import collect_panel_params

__all__ = ["run_panel_coverage"]


def run_panel_coverage(algorithm_instance, prefix, parameters, context, feedback,
                      elev, south, north, west, east, shared_clutter_grid=None):
    """Run compute_coverage for one panel and return the result tuple.

    If *shared_clutter_grid* is provided, it is used instead of downloading
    a new clutter grid for this panel. This ensures both panels in a
    comparison use identical clutter data.
    """
    p = collect_panel_params(algorithm_instance, prefix, parameters, context)

    if shared_clutter_grid is not None:
        clutter_grid = shared_clutter_grid
    elif p.clutter_raster_path:
        clutter_grid = LandCoverGrid.from_raster(p.clutter_raster_path)
    else:
        clutter_grid = None

    validate_itm_input_ranges(
        tx_height_m=p.tx_h,
        rx_height_m=p.rx_h,
        frequency_mhz=p.f_mhz,
        surface_refractivity_n0=p.n0,
        earth_conductivity_sigma=p.sigma,
    )

    feedback.pushInfo(
        f"[{prefix}] TX: ({p.tx_lat:.5f}, {p.tx_lon:.5f}), "
        f"F={p.f_mhz:.1f} MHz, R={p.radius_km:.1f} km, "
        f"Grid={p.grid_size}x{p.grid_size}"
    )

    if clutter_grid is None and p.clutter_enabled:
        clutter_grid = ensure_clutter_grid_for_area(
            south=south, north=north, west=west, east=east, feedback=feedback,
        )
    if clutter_grid is None and p.clutter_enabled:
        raise QgsProcessingException(
            f"{prefix}: Failed to load clutter grid. Coverage comparison "
            "requires identical clutter data for both panels."
        )

    clutter_source = clutter_source_label(
        enabled=p.clutter_enabled, land_cover_grid=clutter_grid,
        raster_path=p.clutter_raster_path,
        tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override,
    )
    clutter_context = None
    if p.clutter_enabled:
        from NoWires.clutter.context import build_initial_clutter_context
        clutter_context = build_initial_clutter_context(
            frequency_mhz=p.f_mhz, tx_height_m=p.tx_h, rx_height_m=p.rx_h,
            tx_ground_elevation_m=0.0, polarization=p.polarization,
            cch_override_m=p.cch_override_m, model=p.clutter_model,
            percentile=p.clutter_percentile, street_width_m=p.street_width_m,
            bel_enabled=p.bel_enabled, bel_building_type=p.bel_building_type,
            bel_elevation_angle_deg=p.bel_elevation_angle_deg)
    tx_clutter_for_report = compute_terminal_clutter_losses(
        tx_lat=p.tx_lat, tx_lon=p.tx_lon, rx_lat=p.tx_lat, rx_lon=p.tx_lon,
        frequency_mhz=p.f_mhz, enabled=p.clutter_enabled,
        land_cover_grid=clutter_grid,
        tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override,
        context=clutter_context,
    )

    try:
        result = compute_coverage(
            elev_grid=elev, tx_lat=p.tx_lat, tx_lon=p.tx_lon,
            tx_h_m=p.tx_h, rx_h_m=p.rx_h, f_mhz=p.f_mhz,
            grid_size=p.grid_size, radius_km=p.radius_km,
            profile_step_m=coverage_profile_step_m(p.f_mhz),
            max_profile_pts=DEFAULT_MAX_PROFILE_PTS,
            tx_power_dbm=p.tx_power, tx_gain_dbi=p.tx_gain,
            rx_gain_dbi=p.rx_gain, cable_loss_db=p.cable_loss,
            rx_sensitivity_dbm=p.rx_sens,
            antenna_az_deg=p.antenna_az,
            antenna_beamwidth_deg=p.antenna_bw_override,
            polarization=p.polarization, climate=p.climate,
            N0=p.n0, epsilon=p.epsilon, sigma=p.sigma,
            time_pct=p.time_pct, location_pct=p.location_pct,
            situation_pct=p.situation_pct,
            antenna_preset=p.antenna_preset,
            antenna_front_back_db=p.front_back_db,
            antenna_downtilt_deg=p.downtilt_deg,
            antenna_horizontal_pattern_path=p.h_pattern,
            antenna_vertical_pattern_path=p.v_pattern,
            clutter_enabled=p.clutter_enabled, clutter_grid=clutter_grid,
            tx_clutter_override=p.tx_clutter_override,
            rx_clutter_override=p.rx_clutter_override,
            tx_clutter_loss_db=tx_clutter_for_report.tx_loss_db,
            clutter_model=p.clutter_model,
            cch_override_m=p.cch_override_m,
            clutter_percentile=p.clutter_percentile,
            street_width_m=p.street_width_m,
            bel_enabled=p.bel_enabled,
            bel_building_type=p.bel_building_type,
            bel_elevation_angle_deg=p.bel_elevation_angle_deg,
            feedback=feedback,
        )
    finally:
        if clutter_grid is not None and shared_clutter_grid is None:
            clutter_grid.close()

    return {
        "result": result,
        "clutter_source": clutter_source,
        "tx_clutter_for_report": tx_clutter_for_report,
        "clutter_enabled": p.clutter_enabled,
        "clutter_model": p.clutter_model,
        "antenna_preset": p.antenna_preset,
        "tx_lat": p.tx_lat, "tx_lon": p.tx_lon,
        "tx_h": p.tx_h, "rx_h": p.rx_h,
        "f_mhz": p.f_mhz, "radius_km": p.radius_km,
        "grid_size": p.grid_size, "polarization": p.polarization,
        "time_pct": p.time_pct, "location_pct": p.location_pct,
        "situation_pct": p.situation_pct,
        "tx_power": p.tx_power, "tx_gain": p.tx_gain, "rx_gain": p.rx_gain,
        "cable_loss": p.cable_loss, "rx_sens": p.rx_sens,
    }
