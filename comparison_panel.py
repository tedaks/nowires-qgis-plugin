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


Coverage Comparison Algorithm — Panel coverage runner.

Standalone function to run compute_coverage for one panel of the comparison.
"""

from qgis.core import QgsCoordinateReferenceSystem

from .coverage_compute import (
    DEFAULT_MAX_PROFILE_PTS,
    coverage_profile_step_m,
)
from .coverage_engine import compute_coverage
from .clutter import (
    LandCoverGrid,
    clutter_source_label,
    clutter_override_value,
    compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area,
)
from .radio import validate_itm_input_ranges
from .antenna import CUSTOM_ANTENNA_PRESET_INDEX
from .comparison_params import GRID_SIZE_PRESETS

__all__ = ["run_panel_coverage"]


def run_panel_coverage(algorithm_instance, prefix, parameters, context, feedback, elev, south, north, west, east):
    """Run compute_coverage for one panel and return the result tuple."""
    tx_point = algorithm_instance.parameterAsPoint(
        parameters,
        f"{prefix}_POINT",
        context,
        crs=QgsCoordinateReferenceSystem("EPSG:4326"),
    )
    if tx_point is None:
        raise ValueError(f"{prefix} TX point is required.")

    tx_lat = tx_point.y()
    tx_lon = tx_point.x()

    tx_h = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_TX_HEIGHT", context)
    rx_h = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_RX_HEIGHT", context)
    f_mhz = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_FREQ_MHZ", context)
    radius_km = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_RADIUS_KM", context)
    grid_size_index = algorithm_instance.parameterAsEnum(parameters, f"{prefix}_GRID_SIZE", context)
    grid_size = GRID_SIZE_PRESETS[grid_size_index]
    polarization = algorithm_instance.parameterAsEnum(parameters, f"{prefix}_POLARIZATION", context)
    climate = algorithm_instance.parameterAsEnum(parameters, f"{prefix}_CLIMATE", context)
    time_pct = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_TIME_PCT", context)
    location_pct = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_LOCATION_PCT", context)
    situation_pct = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_SITUATION_PCT", context)
    tx_power = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_TX_POWER", context)
    tx_gain = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_TX_GAIN", context)
    rx_gain = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_RX_GAIN", context)
    cable_loss = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_CABLE_LOSS", context)
    rx_sens = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_RX_SENSITIVITY", context)
    antenna_bw = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_ANTENNA_BW", context)

    antenna_az = None
    if antenna_bw < 360.0:
        antenna_az = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_ANTENNA_AZ", context)

    antenna_preset = algorithm_instance.parameterAsEnum(parameters, f"{prefix}_ANTENNA_PRESET", context)
    front_back_db = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_FRONT_BACK_DB", context)
    downtilt_deg = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_DOWNTILT_DEG", context)
    h_pattern = algorithm_instance.parameterAsFile(parameters, f"{prefix}_H_PATTERN", context)
    v_pattern = algorithm_instance.parameterAsFile(parameters, f"{prefix}_V_PATTERN", context)
    clutter_enabled = algorithm_instance.parameterAsEnum(parameters, f"{prefix}_CLUTTER_MODEL", context) == 1
    clutter_raster_path = algorithm_instance.parameterAsFile(parameters, f"{prefix}_CLUTTER_RASTER", context)
    if clutter_raster_path:
        clutter_grid = LandCoverGrid.from_raster(clutter_raster_path)
    else:
        clutter_grid = None
    tx_clutter_override = clutter_override_value(
        algorithm_instance.parameterAsEnum(parameters, f"{prefix}_TX_CLUTTER_OVERRIDE", context)
    )
    rx_clutter_override = clutter_override_value(
        algorithm_instance.parameterAsEnum(parameters, f"{prefix}_RX_CLUTTER_OVERRIDE", context)
    )

    antenna_bw_override = (
        None
        if antenna_preset != CUSTOM_ANTENNA_PRESET_INDEX and antenna_bw == 360.0
        else antenna_bw
    )

    n0 = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_N0", context)
    epsilon = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_EPSILON", context)
    sigma = algorithm_instance.parameterAsDouble(parameters, f"{prefix}_SIGMA", context)

    validate_itm_input_ranges(
        tx_height_m=tx_h,
        rx_height_m=rx_h,
        frequency_mhz=f_mhz,
        surface_refractivity_n0=n0,
        earth_conductivity_sigma=sigma,
    )

    feedback.pushInfo(
        f"[{prefix}] TX: ({tx_lat:.5f}, {tx_lon:.5f}), F={f_mhz:.1f} MHz, R={radius_km:.1f} km, Grid={grid_size}x{grid_size}"
    )

    if clutter_grid is None and clutter_enabled:
        clutter_grid = ensure_clutter_grid_for_area(
            south=south,
            north=north,
            west=west,
            east=east,
            feedback=feedback,
        )

    clutter_source = clutter_source_label(
        enabled=clutter_enabled,
        land_cover_grid=clutter_grid,
        raster_path=clutter_raster_path,
        tx_override=tx_clutter_override,
        rx_override=rx_clutter_override,
    )
    tx_clutter_for_report = compute_terminal_clutter_losses(
        tx_lat=tx_lat,
        tx_lon=tx_lon,
        rx_lat=tx_lat,
        rx_lon=tx_lon,
        frequency_mhz=f_mhz,
        enabled=clutter_enabled,
        land_cover_grid=clutter_grid,
        tx_override=tx_clutter_override,
        rx_override=rx_clutter_override,
    )

    result = compute_coverage(
        elev_grid=elev,
        tx_lat=tx_lat,
        tx_lon=tx_lon,
        tx_h_m=tx_h,
        rx_h_m=rx_h,
        f_mhz=f_mhz,
        grid_size=grid_size,
        radius_km=radius_km,
        profile_step_m=coverage_profile_step_m(f_mhz),
        max_profile_pts=DEFAULT_MAX_PROFILE_PTS,
        tx_power_dbm=tx_power,
        tx_gain_dbi=tx_gain,
        rx_gain_dbi=rx_gain,
        cable_loss_db=cable_loss,
        rx_sensitivity_dbm=rx_sens,
        antenna_az_deg=antenna_az,
        antenna_beamwidth_deg=antenna_bw_override,
        polarization=polarization,
        climate=climate,
        N0=n0,
        epsilon=epsilon,
        sigma=sigma,
        time_pct=time_pct,
        location_pct=location_pct,
        situation_pct=situation_pct,
        antenna_preset=antenna_preset,
        antenna_front_back_db=front_back_db,
        antenna_downtilt_deg=downtilt_deg,
        antenna_horizontal_pattern_path=h_pattern,
        antenna_vertical_pattern_path=v_pattern,
        clutter_enabled=clutter_enabled,
        clutter_grid=clutter_grid,
        tx_clutter_override=tx_clutter_override,
        rx_clutter_override=rx_clutter_override,
        feedback=feedback,
    )

    if clutter_grid is not None:
        clutter_grid.close()

    return {
        "result": result,
        "clutter_source": clutter_source,
        "tx_clutter_for_report": tx_clutter_for_report,
        "clutter_enabled": clutter_enabled,
        "antenna_preset": antenna_preset,
        "tx_lat": tx_lat,
        "tx_lon": tx_lon,
        "tx_h": tx_h,
        "rx_h": rx_h,
        "f_mhz": f_mhz,
        "radius_km": radius_km,
        "grid_size": grid_size,
        "polarization": polarization,
        "time_pct": time_pct,
        "location_pct": location_pct,
        "situation_pct": situation_pct,
        "tx_power": tx_power,
        "tx_gain": tx_gain,
        "rx_gain": rx_gain,
        "cable_loss": cable_loss,
        "rx_sens": rx_sens,
    }