# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Core P2P analysis: DEM download, ITM prediction, Fresnel, output, reports."""

import logging
import math
import os
import numpy as np
from osgeo import osr
from qgis.core import QgsProcessingException

from NoWires.constants import (
    CLIMATE_NAMES, DEFAULT_PROFILE_STEP_M, DEGREE_PADDING, METERS_PER_DEGREE_LAT,
    POLARIZATION_NAMES,
)
from NoWires.constants import ITM_LOSS_UPPER_BOUND
from NoWires.temp_manager import TempDirManager
from NoWires.dem_downloader import ensure_dem_for_area, get_temp_dir
from NoWires.elevation import ElevationGrid, bearing_deg, haversine_m
from NoWires.fresnel import C_LIGHT, fresnel_profile_analysis
from NoWires.geo_bounds import shortest_longitude_bounds
from NoWires.p2p.analysis_params import P2PAnalysisParams
from NoWires.radio import PROP_MODE_NAMES, build_pfl, itm_p2p_loss
from NoWires.report.payloads import build_p2p_report_payload
from NoWires.antenna import antenna_gain_adjustment_db
from NoWires.clutter import (compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area)
from NoWires.p2p.params import report_p2p_results
from NoWires.processing_utils import queue_layer_for_loading, register_destination_layer
from NoWires.p2p.chart import show_profile_chart
from NoWires.p2p._outputs_internal import _write_p2p_output_layers, _write_p2p_reports

logger = logging.getLogger(__name__)
__all__ = ["run_p2p_analysis"]
_MIN_P2P_DISTANCE_M = 1.0


def _interpolate_nan_elevations(elevations):
    """Replace NaN values with linearly interpolated neighbours.

    Falls back to nearest valid value at edges. Returns unchanged if all NaN.
    Delegates to shared nan_utils module to avoid code duplication.
    """
    from NoWires.nan_utils import interpolate_nan_elevations
    return interpolate_nan_elevations(elevations)


def _load_p2p_qgis_layers(context, profile_path, fresnel_poly_path,
        fresnel_lines_path, markers_path, show_chart, chart_kwargs, sink,
        feedback=None):
    from qgis.core import QgsVectorLayer
    from NoWires.p2p.symbology import (
        apply_fresnel_polygon_symbology, apply_fresnel_lines_symbology,
        apply_profile_line_symbology,
    )
    link_name = "P2P Link ({:.0f} MHz, {:.1f} km)".format(
        chart_kwargs["f_mhz"], chart_kwargs["dist_m"] / 1000)
    # (path, name, styler) for the three declared vector destinations.
    for path, name, styler in (
        (fresnel_poly_path, "Fresnel Zone Analysis", apply_fresnel_polygon_symbology),
        (profile_path, link_name, apply_profile_line_symbology),
        (markers_path, "P2P TX/RX Markers", None),
    ):
        pp = register_destination_layer(context, path, name, styler=styler)
        if pp is not None:
            sink.append(pp)
            continue
        layer = QgsVectorLayer(path, name)
        if styler is not None and layer.isValid():
            styler(layer)
        queue_layer_for_loading(context, layer, name)
    # Fresnel lines is a derived sidecar — queue manually.
    fresnel_lines_layer = QgsVectorLayer(fresnel_lines_path, "Fresnel Zone Lines")
    if fresnel_lines_layer.isValid():
        apply_fresnel_lines_symbology(fresnel_lines_layer)
    queue_layer_for_loading(context, fresnel_lines_layer, "Fresnel Zone Lines")
    if show_chart:
        try:
            show_profile_chart(**chart_kwargs)
        except Exception:
            logger.warning("P2P profile chart failed", exc_info=True)
            if feedback is not None:
                feedback.pushWarning("P2P profile chart creation failed")


def run_p2p_analysis(params: P2PAnalysisParams):
    p = params
    dist_m = haversine_m(p.tx_lat, p.tx_lon, p.rx_lat, p.rx_lon)
    if dist_m < _MIN_P2P_DISTANCE_M:
        raise QgsProcessingException(
            "TX and RX points are too close ({:.2f} m); "
            "minimum path distance is {:.0f} m.".format(dist_m, _MIN_P2P_DISTANCE_M))
    p.feedback.pushInfo("TX: ({:.5f}, {:.5f}), RX: ({:.5f}, {:.5f})".format(
        p.tx_lat, p.tx_lon, p.rx_lat, p.rx_lon))
    p.feedback.pushInfo("Path distance: {:.1f} m ({:.2f} km)".format(
        dist_m, dist_m / 1000.0))
    pad = max(DEGREE_PADDING, dist_m / METERS_PER_DEGREE_LAT * 0.1)
    south, north = min(p.tx_lat, p.rx_lat) - pad, max(p.tx_lat, p.rx_lat) + pad
    west, east = shortest_longitude_bounds(p.tx_lon, p.rx_lon, padding_deg=pad)
    clutter_grid = p.clutter_grid
    owns_clutter_grid = False
    if clutter_grid is None and p.clutter_enabled:
        clutter_grid = ensure_clutter_grid_for_area(
            south=south, north=north, west=west, east=east, feedback=p.feedback)
        owns_clutter_grid = clutter_grid is not None
    needs_temp_dir = not (p.profile_dest and p.fresnel_dest and p.markers_dest)
    tmp_mgr = TempDirManager()
    try:
        p.feedback.pushInfo("Downloading DEM data for path...")
        p.feedback.setProgress(5)
        dem_path = ensure_dem_for_area(
            south, north, west, east, feedback=p.feedback)
        if dem_path is None:
            raise QgsProcessingException(
                "Failed to obtain DEM data for the path area.")
        p.feedback.setProgress(30)
        p.feedback.pushInfo("Building elevation grid...")
        with ElevationGrid(dem_path) as elev:
            points = elev.terrain_profile(
                p.tx_lat, p.tx_lon, p.rx_lat, p.rx_lon, step_m=DEFAULT_PROFILE_STEP_M)
        if len(points) < 2:
            raise QgsProcessingException("Terrain profile too short.")
        distances = [pt[0] for pt in points]
        elevations = [pt[1] for pt in points]
        nan_count = sum(1 for e in elevations if math.isnan(e))
        if nan_count > 0:
            if nan_count == len(elevations):
                raise QgsProcessingException(
                    "All {} elevation samples are NaN — "
                    "DEM data is missing for this path.".format(nan_count))
            p.feedback.pushInfo(
                "Interpolating {} NaN elevation value(s) from nearest "
                "valid samples (missing DEM data)".format(nan_count))
            logger.warning(
                "Interpolating %d NaN elevation value(s) from nearest "
                "valid samples (missing DEM data)", nan_count)
            elevations = _interpolate_nan_elevations(elevations)
        step_m_val = dist_m / max(len(distances) - 1, 1)
        pfl = build_pfl(elevations, step_m_val)
        p.feedback.setProgress(50)
        result = itm_p2p_loss(h_tx__meter=p.tx_h, h_rx__meter=p.rx_h, profile=pfl,
            climate=p.climate, N0=p.n0, f__mhz=p.f_mhz, polarization=p.polarization,
            epsilon=p.epsilon, sigma=p.sigma, time_pct=p.time_pct,
            location_pct=p.location_pct, situation_pct=p.situation_pct)
        if result.failed or not math.isfinite(result.loss_db):
            raise QgsProcessingException(
                "ITM prediction failed (loss_db={:.1f}, mode={}, "
                "warnings={}).".format(result.loss_db, result.mode, result.warnings))
        if result.loss_db > ITM_LOSS_UPPER_BOUND:
            logger.debug("ITM loss %.1f dB exceeds cap (%.1f); capping",
                         result.loss_db, ITM_LOSS_UPPER_BOUND)
        loss_db = min(result.loss_db, ITM_LOSS_UPPER_BOUND)
        tx_elev, rx_elev = elevations[0], elevations[-1]
        tx_ant_h, rx_ant_h = tx_elev + p.tx_h, rx_elev + p.rx_h
        wavelength_m = C_LIGHT / (p.f_mhz * 1e6)
        dist_arr = np.asarray(distances, dtype=np.float64)
        elev_arr = np.asarray(elevations, dtype=np.float64)
        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                dist_arr, elev_arr, tx_ant_h, rx_ant_h,
                dist_m, wavelength_m, p.k_factor))
        los_blocked = bool(obstructs.any())
        f1_violated = bool(vf1.any())
        f60_violated = bool(vf60.any())
        eirp_dbm = p.tx_power + p.tx_gain - p.cable_loss
        tx_bearing = bearing_deg(p.tx_lat, p.tx_lon, p.rx_lat, p.rx_lon)
        rx_bearing = bearing_deg(p.rx_lat, p.rx_lon, p.tx_lat, p.tx_lon)
        vert_angle = math.degrees(math.atan2(
            (rx_elev + p.rx_h) - (tx_elev + p.tx_h), max(dist_m, 1.0)))
        ant_adj_total = (
            antenna_gain_adjustment_db(tx_bearing, vert_angle, p.tx_antenna_config)
            + antenna_gain_adjustment_db(rx_bearing, -vert_angle, p.rx_antenna_config))
        clutter_context = None
        if p.clutter_enabled:
            from NoWires.clutter.context import build_link_clutter_context
            clutter_context = build_link_clutter_context(
                params=p, dist_m=dist_m, tx_h=p.tx_h, rx_h=p.rx_h,
                tx_elev=float(tx_elev), rx_elev=float(rx_elev))
        cl = compute_terminal_clutter_losses(
            tx_lat=p.tx_lat, tx_lon=p.tx_lon, rx_lat=p.rx_lat, rx_lon=p.rx_lon,
            frequency_mhz=p.f_mhz, enabled=p.clutter_enabled,
            land_cover_grid=clutter_grid, tx_override=p.tx_clutter_override,
            rx_override=p.rx_clutter_override, context=clutter_context)
        total_path_loss_db = loss_db + cl.total_with_bel_db
        prx_dbm = eirp_dbm + p.rx_gain + ant_adj_total - total_path_loss_db
        margin_db = prx_dbm - p.rx_sens
        fspl_db = 20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(p.f_mhz) + 32.45
        p.feedback.setProgress(70)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if needs_temp_dir:
            temp_dir = os.path.join(get_temp_dir(), "p2p_outputs")
            os.makedirs(temp_dir, exist_ok=True)
            tmp_mgr.add_dir(temp_dir, persistent=True)
        else:
            temp_dir = None
        profile_path, fresnel_poly_path, fresnel_lines_path, markers_path = _write_p2p_output_layers(
                srs, dict(profile_dest=p.profile_dest, fresnel_dest=p.fresnel_dest,
                    markers_dest=p.markers_dest, temp_dir=temp_dir),
                p.tx_lat, p.tx_lon, p.rx_lat, p.rx_lon, dist_m, result,
                dist_arr, terrain_bulge, los_h, fresnel_r,
                p.tx_h, p.rx_h, p.tx_gain, p.rx_gain, p.tx_power, p.rx_sens,
                itm_loss_db=loss_db)
        report_payload = build_p2p_report_payload(
            tx_lat=p.tx_lat, tx_lon=p.tx_lon, rx_lat=p.rx_lat, rx_lon=p.rx_lon,
            tx_h=p.tx_h, rx_h=p.rx_h, f_mhz=p.f_mhz,
            polarization_name=POLARIZATION_NAMES.get(p.polarization, str(p.polarization)),
            climate_name=CLIMATE_NAMES.get(p.climate, str(p.climate)),
            k_factor=p.k_factor, dist_m=dist_m, propagation_mode=result.mode,
            propagation_mode_name=PROP_MODE_NAMES.get(result.mode, "Unknown"),
            fspl_db=fspl_db, itm_loss_db=loss_db,
            tx_power=p.tx_power, tx_gain=p.tx_gain, rx_gain=p.rx_gain,
            cable_loss=p.cable_loss, eirp_dbm=eirp_dbm,
            prx_dbm=prx_dbm, rx_sensitivity_dbm=p.rx_sens,
            margin_db=margin_db, los_blocked=los_blocked,
            fresnel_1_violated=f1_violated, fresnel_60_violated=f60_violated,
            max_fresnel_radius_m=float(fresnel_r.max()),
            total_path_loss_db=total_path_loss_db,
            clutter_tx_db=cl.tx_loss_db, clutter_rx_db=cl.rx_loss_db,
            clutter_source=cl.source,
            tx_antenna_preset=p.tx_antenna_config.preset if p.tx_antenna_config is not None else "omni",
            rx_antenna_preset=p.rx_antenna_config.preset if p.rx_antenna_config is not None else "omni",
            antenna_gain_adjustment_db=ant_adj_total,
            tx_cch_m=cl.tx_cch_m, rx_cch_m=cl.rx_cch_m,
            clutter_method=cl.method, clutter_percentile=cl.percentile,
            bel_rx_db=cl.rx_bel_db)
        _write_p2p_reports(p.report_csv_path, p.report_json_path,
                           p.report_html_path, report_payload)
        p.feedback.setProgress(90)
        chart_kwargs = dict(distances=dist_arr, elevations=elev_arr,
            terrain_bulge=terrain_bulge, los_h=los_h, fresnel_r=fresnel_r,
            dist_m=dist_m, tx_h=p.tx_h, rx_h=p.rx_h, f_mhz=p.f_mhz,
            result=result, k_factor=p.k_factor,
            tx_power=p.tx_power, tx_gain=p.tx_gain, rx_gain=p.rx_gain,
            cable_loss=p.cable_loss, rx_sens=p.rx_sens,
            prx_dbm=prx_dbm, margin_db=margin_db, itm_loss_db=loss_db)
        _load_p2p_qgis_layers(p.context, profile_path, fresnel_poly_path,
            fresnel_lines_path, markers_path, p.show_chart, chart_kwargs,
            p.post_processor_sink, feedback=p.feedback)
        p.feedback.setProgress(100)
        report_p2p_results(p.feedback, dist_m, p.f_mhz, result,
                           report_payload, p.k_factor, los_blocked,
                           float(fresnel_r.max()))
        return {
            p.output_profile: profile_path,
            p.output_fresnel: fresnel_poly_path,
            p.output_markers: markers_path,
            p.output_report_csv: p.report_csv_path,
            p.output_report_json: p.report_json_path,
            p.output_report_html: p.report_html_path,
        }
    finally:
        if owns_clutter_grid and clutter_grid is not None:
            try:
                clutter_grid.close()
            except Exception:
                logger.warning("Failed to close clutter grid", exc_info=True)
        tmp_mgr.cleanup()
        tmp_mgr.warn_persistent(p.feedback)
