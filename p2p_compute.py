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


Core P2P analysis execution: DEM download, ITM prediction, Fresnel analysis,
output writing, report generation, chart display, and feedback reporting.
"""

import math
import os
import tempfile

import numpy as np
from osgeo import osr

from .constants import (
    CLIMATE_NAMES, DEFAULT_PROFILE_STEP_M, DEGREE_PADDING, METERS_PER_DEGREE_LAT,
    POLARIZATION_NAMES,
)
from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid, bearing_deg, haversine_m
from .fresnel import C_LIGHT
from .p2p_analysis_params import P2PAnalysisParams
from .radio import (PROP_MODE_NAMES, build_pfl,
    fresnel_profile_analysis, itm_p2p_loss)
from .report_export import write_report_csv, write_report_html, write_report_json
from .report_payloads import build_p2p_report_payload
from .report_markers import write_p2p_marker_layer
from .antenna import antenna_gain_adjustment_db
from .clutter import (compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area)
from .processing_utils import queue_layer_for_loading
from .p2p_params import report_p2p_results
from .p2p_outputs import write_profile_line, write_fresnel_zone
from .p2p_chart import show_profile_chart

__all__ = ["run_p2p_analysis"]


def _write_p2p_output_layers(srs, paths, tx_lat, tx_lon, rx_lat, rx_lon,
        dist_m, result, dist_arr, terrain_bulge, los_h, fresnel_r,
        tx_h, rx_h, tx_gain, rx_gain, tx_power, rx_sens):
    profile_path = (
        paths["profile_dest"] or os.path.join(paths["temp_dir"], "profile_line.shp"))
    write_profile_line(
        profile_path, srs, tx_lat, tx_lon, rx_lat, rx_lon, dist_m, result)
    fresnel_poly_path = (
        paths["fresnel_dest"] or os.path.join(paths["temp_dir"], "fresnel_zone.shp"))
    markers_path = (
        paths["markers_dest"] or os.path.join(paths["temp_dir"], "p2p_markers.shp"))
    _poly_root, _poly_ext = os.path.splitext(fresnel_poly_path)
    fresnel_lines_path = "{}_lines{}".format(_poly_root, _poly_ext)
    write_fresnel_zone(fresnel_poly_path, fresnel_lines_path, srs,
        tx_lat, tx_lon, rx_lat, rx_lon,
        dist_arr, terrain_bulge, los_h, fresnel_r, dist_m)
    write_p2p_marker_layer(markers_path,
        tx_lat=tx_lat, tx_lon=tx_lon, rx_lat=rx_lat, rx_lon=rx_lon,
        tx_h=tx_h, rx_h=rx_h, tx_gain=tx_gain, rx_gain=rx_gain,
        tx_power_dbm=tx_power, rx_sensitivity_dbm=rx_sens)
    return profile_path, fresnel_poly_path, markers_path


def _write_p2p_reports(report_csv_path, report_json_path, report_html_path,
        report_payload):
    if report_csv_path:
        write_report_csv(report_csv_path, report_payload)
    if report_json_path:
        write_report_json(report_json_path, report_payload)
    if report_html_path:
        write_report_html(report_html_path, report_payload, title="NoWires P2P Report")


def _load_p2p_qgis_layers(context, profile_path, fresnel_poly_path,
        fresnel_lines_path, markers_path, show_chart, chart_kwargs):
    from qgis.core import QgsVectorLayer
    f_mhz = chart_kwargs["f_mhz"]
    dist_m = chart_kwargs["dist_m"]
    link_name = "P2P Link ({:.0f} MHz, {:.1f} km)".format(f_mhz, dist_m / 1000)
    profile_layer = QgsVectorLayer(profile_path, link_name)
    fresnel_poly_layer = QgsVectorLayer(fresnel_poly_path, "Fresnel Zone Analysis")
    fresnel_lines_layer = QgsVectorLayer(fresnel_lines_path, "Fresnel Zone Lines")
    marker_layer = QgsVectorLayer(markers_path, "P2P TX/RX Markers")
    queue_layer_for_loading(context, fresnel_poly_layer, "Fresnel Zone Analysis")
    queue_layer_for_loading(context, fresnel_lines_layer, "Fresnel Zone Lines")
    queue_layer_for_loading(context, profile_layer, link_name)
    queue_layer_for_loading(context, marker_layer, "P2P TX/RX Markers")
    if show_chart:
        show_profile_chart(**chart_kwargs)


def run_p2p_analysis(params: P2PAnalysisParams):
    tx_lat = params.tx_lat
    tx_lon = params.tx_lon
    rx_lat = params.rx_lat
    rx_lon = params.rx_lon
    tx_h = params.tx_h
    rx_h = params.rx_h
    f_mhz = params.f_mhz
    polarization = params.polarization
    climate = params.climate
    time_pct = params.time_pct
    location_pct = params.location_pct
    situation_pct = params.situation_pct
    tx_power = params.tx_power
    tx_gain = params.tx_gain
    rx_gain = params.rx_gain
    cable_loss = params.cable_loss
    rx_sens = params.rx_sens
    k_factor = params.k_factor
    n0 = params.n0
    epsilon = params.epsilon
    sigma = params.sigma
    tx_antenna_config = params.tx_antenna_config
    rx_antenna_config = params.rx_antenna_config
    clutter_enabled = params.clutter_enabled
    clutter_grid = params.clutter_grid
    tx_clutter_override = params.tx_clutter_override
    rx_clutter_override = params.rx_clutter_override
    profile_dest = params.profile_dest
    fresnel_dest = params.fresnel_dest
    markers_dest = params.markers_dest
    report_csv_path = params.report_csv_path
    report_json_path = params.report_json_path
    report_html_path = params.report_html_path
    show_chart = params.show_chart
    context = params.context
    feedback = params.feedback
    dist_m = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)
    feedback.pushInfo("TX: ({:.5f}, {:.5f}), RX: ({:.5f}, {:.5f})".format(
        tx_lat, tx_lon, rx_lat, rx_lon))
    feedback.pushInfo("Path distance: {:.1f} m ({:.2f} km)".format(
        dist_m, dist_m / 1000.0))
    pad = max(DEGREE_PADDING, dist_m / METERS_PER_DEGREE_LAT * 0.1)
    south = min(tx_lat, rx_lat) - pad
    north = max(tx_lat, rx_lat) + pad
    west = min(tx_lon, rx_lon) - pad
    east = max(tx_lon, rx_lon) + pad
    if clutter_grid is None and clutter_enabled:
        clutter_grid = ensure_clutter_grid_for_area(
            south=south, north=north, west=west, east=east, feedback=feedback)
    feedback.pushInfo("Downloading DEM data for path...")
    feedback.setProgress(5)
    dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
    if dem_path is None:
        raise RuntimeError("Failed to obtain DEM data for the path area.")
    feedback.setProgress(30)
    feedback.pushInfo("Building elevation grid...")
    elev = ElevationGrid(dem_path)
    feedback.pushInfo("Generating terrain profile...")
    points = elev.terrain_profile(tx_lat, tx_lon, rx_lat, rx_lon, step_m=DEFAULT_PROFILE_STEP_M)
    if len(points) < 2:
        raise RuntimeError("Terrain profile too short.")
    distances = [p[0] for p in points]
    elevations = [p[1] for p in points]
    elevations = [0.0 if math.isnan(e) else e for e in elevations]
    step_m_val = dist_m / max(len(distances) - 1, 1)
    pfl = build_pfl(elevations, step_m_val)
    feedback.pushInfo("Running ITM prediction...")
    feedback.setProgress(50)
    result = itm_p2p_loss(h_tx__meter=tx_h, h_rx__meter=rx_h, profile=pfl,
        climate=climate, N0=n0, f__mhz=f_mhz, polarization=polarization,
        epsilon=epsilon, sigma=sigma, time_pct=time_pct,
        location_pct=location_pct, situation_pct=situation_pct)
    tx_elev = elevations[0]
    rx_elev = elevations[-1]
    tx_antenna_h = tx_elev + tx_h
    rx_antenna_h = rx_elev + rx_h
    wavelength_m = C_LIGHT / (f_mhz * 1e6)
    dist_arr = np.asarray(distances, dtype=np.float64)
    elev_arr = np.asarray(elevations, dtype=np.float64)
    terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
        fresnel_profile_analysis(dist_arr, elev_arr, tx_antenna_h, rx_antenna_h,
            dist_m, wavelength_m, k_factor))
    los_blocked = bool(obstructs.any())
    f1_violated = bool(vf1.any())
    f60_violated = bool(vf60.any())
    eirp_dbm = tx_power + tx_gain - cable_loss
    tx_bearing = bearing_deg(tx_lat, tx_lon, rx_lat, rx_lon)
    rx_bearing = bearing_deg(rx_lat, rx_lon, tx_lat, tx_lon)
    vertical_angle = math.degrees(
        math.atan2((rx_elev + rx_h) - (tx_elev + tx_h), max(dist_m, 1.0)))
    tx_ant_adj = antenna_gain_adjustment_db(tx_bearing, vertical_angle, tx_antenna_config)
    rx_ant_adj = antenna_gain_adjustment_db(rx_bearing, -vertical_angle, rx_antenna_config)
    antenna_gain_adjustment_db_total = tx_ant_adj + rx_ant_adj
    clutter_losses = compute_terminal_clutter_losses(tx_lat=tx_lat, tx_lon=tx_lon,
        rx_lat=rx_lat, rx_lon=rx_lon, frequency_mhz=f_mhz, enabled=clutter_enabled,
        land_cover_grid=clutter_grid,
        tx_override=tx_clutter_override, rx_override=rx_clutter_override)
    total_path_loss_db = result.loss_db + clutter_losses.total_loss_db
    prx_dbm = eirp_dbm + rx_gain + antenna_gain_adjustment_db_total - total_path_loss_db
    margin_db = prx_dbm - rx_sens
    fspl_db = (20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(f_mhz) + 32.44
        if dist_m > 0 and f_mhz > 0 else 0.0)
    feedback.setProgress(70)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    needs_temp_dir = not (profile_dest and fresnel_dest and markers_dest)
    if needs_temp_dir:
        temp_dir = tempfile.mkdtemp(prefix="nowires_p2p_")
        feedback.pushInfo(
            "Temporary outputs are intentionally left on disk for QGIS layer loading: {}".format(
                temp_dir))
    else:
        temp_dir = None
    profile_path, fresnel_poly_path, markers_path = _write_p2p_output_layers(
            srs, dict(profile_dest=profile_dest, fresnel_dest=fresnel_dest,
                markers_dest=markers_dest, temp_dir=temp_dir),
            tx_lat, tx_lon, rx_lat, rx_lon, dist_m, result,
            dist_arr, terrain_bulge, los_h, fresnel_r,
            tx_h, rx_h, tx_gain, rx_gain, tx_power, rx_sens)
    _poly_root, _poly_ext = os.path.splitext(fresnel_poly_path)
    fresnel_lines_path = "{}_lines{}".format(_poly_root, _poly_ext)
    report_payload = build_p2p_report_payload(
        tx_lat=tx_lat, tx_lon=tx_lon, rx_lat=rx_lat, rx_lon=rx_lon,
        tx_h=tx_h, rx_h=rx_h, f_mhz=f_mhz,
        polarization_name=POLARIZATION_NAMES.get(polarization, str(polarization)),
        climate_name=CLIMATE_NAMES.get(climate, str(climate)),
        k_factor=k_factor, dist_m=dist_m,
        propagation_mode=result.mode,
        propagation_mode_name=PROP_MODE_NAMES.get(result.mode, "Unknown"),
        fspl_db=fspl_db, itm_loss_db=result.loss_db,
        tx_power=tx_power, tx_gain=tx_gain, rx_gain=rx_gain,
        cable_loss=cable_loss, eirp_dbm=eirp_dbm,
        prx_dbm=prx_dbm, rx_sensitivity_dbm=rx_sens,
        margin_db=margin_db, los_blocked=los_blocked,
        fresnel_1_violated=f1_violated, fresnel_60_violated=f60_violated,
        max_fresnel_radius_m=float(fresnel_r.max()),
        total_path_loss_db=total_path_loss_db,
        clutter_tx_db=clutter_losses.tx_loss_db,
        clutter_rx_db=clutter_losses.rx_loss_db,
        clutter_source=clutter_losses.source,
        tx_antenna_preset=tx_antenna_config.preset,
        rx_antenna_preset=rx_antenna_config.preset,
        antenna_gain_adjustment_db=antenna_gain_adjustment_db_total)
    _write_p2p_reports(report_csv_path, report_json_path, report_html_path,
        report_payload)
    feedback.setProgress(90)
    chart_kwargs = dict(distances=dist_arr, elevations=elev_arr,
        terrain_bulge=terrain_bulge, los_h=los_h, fresnel_r=fresnel_r,
        dist_m=dist_m, tx_h=tx_h, rx_h=rx_h, f_mhz=f_mhz,
        result=result, k_factor=k_factor,
        tx_power=tx_power, tx_gain=tx_gain, rx_gain=rx_gain,
        cable_loss=cable_loss, rx_sens=rx_sens,
        prx_dbm=prx_dbm, margin_db=margin_db)
    _load_p2p_qgis_layers(context, profile_path, fresnel_poly_path,
        fresnel_lines_path, markers_path, show_chart, chart_kwargs)
    feedback.setProgress(100)
    report_p2p_results(feedback, dist_m, f_mhz, result, PROP_MODE_NAMES,
        tx_power, tx_gain, cable_loss, eirp_dbm, fspl_db,
        clutter_losses, total_path_loss_db, antenna_gain_adjustment_db_total,
        rx_gain, prx_dbm, rx_sens, margin_db, report_payload,
        k_factor, los_blocked, f1_violated, f60_violated,
        float(fresnel_r.max()))
    return {
        params.output_profile: profile_path,
        params.output_fresnel: fresnel_poly_path,
        params.output_markers: markers_path,
        params.output_report_csv: report_csv_path,
        params.output_report_json: report_json_path,
        params.output_report_html: report_html_path,
    }