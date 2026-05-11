# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coverage Analysis Algorithm — heatmap prediction via ITM."""

import contextlib
import logging
import math
import os

logger = logging.getLogger(__name__)

from qgis.core import Qgis, QgsProcessingException, QgsRasterLayer

from .base_algorithm import NoWiresAlgorithm, install_constants
from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid
from .coverage_legend import show_coverage_legend
from .coverage_compute import DEFAULT_MAX_PROFILE_PTS, coverage_profile_step_m
from .coverage_engine import compute_coverage
from .clutter import (
    CLUTTER_MODEL_OPTIONS, clutter_source_label, compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area,
)
from .report_export import write_report_csv, write_report_html, write_report_json
from .coverage_params import PARAM_CONSTANTS, add_coverage_params, extract_coverage_params
from .antenna import ANTENNA_PRESET_OPTIONS
from .constants import DEGREE_PADDING
from .geo_bounds import coverage_bounds
from .coverage_reporting import (
    build_coverage_report_payload_for_grid, report_coverage_results,
    write_coverage_geotiff,
)
from .processing_utils import queue_layer_for_loading, register_destination_layer
from .temp_manager import TempDirManager


def _validate_dem_coverage(elev, south, north, west, east, feedback):
    """Warn if the DEM does not fully cover the requested analysis bounds."""
    dem_south = min(elev.min_lat, elev.max_lat)
    dem_north = max(elev.min_lat, elev.max_lat)
    dem_west = min(elev.min_lon, elev.max_lon)
    dem_east = max(elev.min_lon, elev.max_lon)
    uncovered_lat = (south < dem_south - 0.01) or (north > dem_north + 0.01)
    uncovered_lon = (west < dem_west - 0.01) or (east > dem_east + 0.01)
    if uncovered_lat or uncovered_lon:
        logger.warning(
            "DEM does not fully cover bounds. DEM: (%.4f,%.4f)-(%.4f,%.4f); "
            "Analysis: (%.4f,%.4f)-(%.4f,%.4f). Edge data may be unreliable.",
            dem_south, dem_west, dem_north, dem_east, south, west, north, east)
        feedback.pushWarning(
            "Downloaded DEM does not fully cover the analysis area. "
            "Results near the edges may be unreliable.")


def _build_clutter_context(p, clutter_grid, elev):
    """Build ClutterLossContext and compute terminal clutter losses."""
    from .clutter_context import ClutterLossContext
    clutter_grid_resolved = clutter_grid
    if clutter_grid_resolved is None and p.clutter_enabled:
        pad_deg = max(DEGREE_PADDING, p.radius_km / 111320.0 * 0.1)
        south, north, west, east = coverage_bounds(
            p.tx_lat, p.tx_lon, p.radius_km, padding_deg=pad_deg)
        clutter_grid_resolved = ensure_clutter_grid_for_area(
            south=south, north=north, west=west, east=east)
    clutter_source = clutter_source_label(
        enabled=p.clutter_enabled, land_cover_grid=clutter_grid_resolved,
        raster_path=p.clutter_raster_path,
        tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override)
    clutter_context = None
    if p.clutter_enabled:
        tx_ground = float(elev.sample(p.tx_lat, p.tx_lon))
        if not math.isfinite(tx_ground):
            tx_ground = 0.0
        # Note: rx_ground_elevation_m is a placeholder (0.0) here. In coverage
        # mode, each pixel gets its own RX ground elevation computed from the
        # DEM during task building (coverage_tasks.py). The context created here
        # is only used for TX-side clutter and the single-point report.
        clutter_context = ClutterLossContext(
            frequency_mhz=p.f_mhz, distance_m=0.0,
            tx_height_m=p.tx_h, rx_height_m=p.rx_h,
            rx_ground_elevation_m=0.0,
            tx_ground_elevation_m=tx_ground,
            polarization=p.polarization, cch_override_m=p.cch_override_m,
            model=p.clutter_model, percentile=p.clutter_percentile,
            street_width_m=p.street_width_m, bel_enabled=p.bel_enabled,
            bel_building_type=p.bel_building_type,
            bel_elevation_angle_deg=p.bel_elevation_angle_deg)
    tx_clutter_for_report = compute_terminal_clutter_losses(
        tx_lat=p.tx_lat, tx_lon=p.tx_lon, rx_lat=p.tx_lat, rx_lon=p.tx_lon,
        frequency_mhz=p.f_mhz, enabled=p.clutter_enabled,
        land_cover_grid=clutter_grid_resolved,
        tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override,
        context=clutter_context)
    return clutter_grid_resolved, clutter_context, clutter_source, tx_clutter_for_report


def _write_coverage_outputs(algorithm, parameters, context, feedback, p, result,
                            dem_path, clutter_source, tx_clutter_for_report):
    """Write coverage raster, reports, and load QGIS layers."""
    tif_path = algorithm.parameterAsOutputLayer(parameters, algorithm.OUTPUT_RASTER, context)
    if not tif_path:
        tif_path = os.path.join(
            algorithm._tmp.make_dir("coverage_prx", persistent=True), "coverage_prx.tif")
        algorithm._tmp.warn_persistent(feedback)
    report_csv_path = algorithm.parameterAsFileOutput(
        parameters, algorithm.OUTPUT_REPORT_CSV, context)
    report_json_path = algorithm.parameterAsFileOutput(
        parameters, algorithm.OUTPUT_REPORT_JSON, context)
    report_html_path = algorithm.parameterAsFileOutput(
        parameters, algorithm.OUTPUT_REPORT_HTML, context)

    report_payload, raster_grid, valid, summary = (
        build_coverage_report_payload_for_grid(
            prx_grid=result.prx_grid, loss_grid=result.loss_grid,
            itm_loss_grid=result.itm_loss_grid,
            clutter_loss_grid=result.clutter_loss_grid,
            clutter_rx_db_grid=result.clutter_rx_db_grid,
            bel_rx_db_grid=result.bel_rx_db_grid,
            min_lat=result.min_lat, max_lat=result.max_lat,
            min_lon=result.min_lon, max_lon=result.max_lon,
            tx_lat=p.tx_lat, tx_lon=p.tx_lon, tx_h=p.tx_h, rx_h=p.rx_h,
            f_mhz=p.f_mhz, radius_km=p.radius_km, grid_size=p.grid_size,
            polarization=p.polarization, climate=p.climate,
            time_pct=p.time_pct, location_pct=p.location_pct,
            situation_pct=p.situation_pct, tx_power=p.tx_power,
            tx_gain=p.tx_gain, rx_gain=p.rx_gain, cable_loss=p.cable_loss,
            rx_sens=p.rx_sens, clutter_enabled=p.clutter_enabled,
            clutter_model=p.clutter_model, antenna_preset=p.antenna_preset,
            clutter_source=clutter_source,
            tx_clutter_for_report=tx_clutter_for_report))

    write_coverage_geotiff(result.prx_grid, result.min_lat, result.max_lat,
                           result.min_lon, result.max_lon, tif_path)
    layer_name = "Coverage ({:.0f} MHz, {:.0f} km, {}x{})".format(
        p.f_mhz, p.radius_km, p.grid_size, p.grid_size)
    raster_layer = QgsRasterLayer(tif_path, layer_name)
    if raster_layer.isValid():
        dem_layer = QgsRasterLayer(dem_path, "NoWires DEM (GLO-30)")
        if dem_layer.isValid():
            elev_props = dem_layer.elevationProperties()
            elev_props.setEnabled(True)
            elev_props.setMode(Qgis.RasterElevationMode.RepresentsElevationSurface)
            elev_props.setBandNumber(1)
            queue_layer_for_loading(context, dem_layer, "NoWires DEM (GLO-30)")
            algorithm._raster_layer_ids.append(dem_layer.id())
            algorithm._dem_layer_id = dem_layer.id()
        pp = register_destination_layer(
            context, tif_path, layer_name, styler=algorithm._on_coverage_loaded)
        if pp is not None:
            algorithm._coverage_post_processor = pp
        else:
            algorithm._on_coverage_loaded(raster_layer)
            queue_layer_for_loading(context, raster_layer, layer_name)
        show_coverage_legend(rx_sensitivity_dbm=p.rx_sens)
    else:
        feedback.pushWarning(
            "Could not load coverage raster layer: {}".format(raster_layer.error().summary()))
    report_coverage_results(feedback, report_payload, raster_grid, valid, p.rx_sens,
                            summary=summary)
    if report_csv_path:
        write_report_csv(report_csv_path, report_payload)
    if report_json_path:
        write_report_json(report_json_path, report_payload)
    if report_html_path:
        write_report_html(report_html_path, report_payload, title="NoWires Coverage Report")
    return {
        algorithm.OUTPUT_RASTER: tif_path,
        algorithm.OUTPUT_REPORT_CSV: report_csv_path,
        algorithm.OUTPUT_REPORT_JSON: report_json_path,
        algorithm.OUTPUT_REPORT_HTML: report_html_path,
    }


class CoverageAlgorithm(NoWiresAlgorithm):
    """Coverage analysis heatmap prediction."""

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []
        self._coverage_post_processor = None

    def initAlgorithm(self, config):
        add_coverage_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        self._raster_layer_ids = []
        self._coverage_post_processor = None
        self._tmp = TempDirManager()
        clutter_grid = None
        p = extract_coverage_params(self, parameters, context)

        feedback.pushInfo(
            "TX: ({:.5f}, {:.5f}), F={:.1f} MHz, R={:.1f} km, Grid={}x{}".format(
                p.tx_lat, p.tx_lon, p.f_mhz, p.radius_km, p.grid_size, p.grid_size))
        feedback.pushInfo("Clutter correction: {}".format(
            CLUTTER_MODEL_OPTIONS[2] if p.clutter_enabled and p.clutter_model == "advanced"
            else CLUTTER_MODEL_OPTIONS[1] if p.clutter_enabled else CLUTTER_MODEL_OPTIONS[0]))
        feedback.pushInfo("TX antenna preset: {}".format(ANTENNA_PRESET_OPTIONS[p.antenna_preset]))

        pad_deg = max(DEGREE_PADDING, p.radius_km / (111320.0 / 1000.0) * 0.1)
        south, north, west, east = coverage_bounds(
            p.tx_lat, p.tx_lon, p.radius_km, padding_deg=pad_deg)

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise QgsProcessingException("Failed to obtain DEM data for the coverage area.")

        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(15)
        try:
            with ElevationGrid(dem_path) as elev:
                _validate_dem_coverage(elev, south, north, west, east, feedback)
                clutter_grid, clutter_context, clutter_source, tx_clutter_for_report = \
                    _build_clutter_context(p, p.clutter_grid, elev)
                feedback.pushInfo("Computing coverage...")
                feedback.setProgress(20)
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
                    situation_pct=p.situation_pct, antenna_preset=p.antenna_preset,
                    antenna_front_back_db=p.front_back_db,
                    antenna_downtilt_deg=p.downtilt_deg,
                    antenna_horizontal_pattern_path=p.h_pattern,
                    antenna_vertical_pattern_path=p.v_pattern,
                    clutter_enabled=p.clutter_enabled, clutter_grid=clutter_grid,
                    tx_clutter_override=p.tx_clutter_override,
                    rx_clutter_override=p.rx_clutter_override,
                    tx_clutter_loss_db=tx_clutter_for_report.tx_loss_db,
                    clutter_model=p.clutter_model, cch_override_m=p.cch_override_m,
                    clutter_percentile=p.clutter_percentile,
                    street_width_m=p.street_width_m, bel_enabled=p.bel_enabled,
                    bel_building_type=p.bel_building_type,
                    bel_elevation_angle_deg=p.bel_elevation_angle_deg,
                    feedback=feedback)
                if result is None or result.prx_grid is None:
                    raise QgsProcessingException("Coverage computation was cancelled.")
                feedback.pushInfo("Writing coverage raster...")
                feedback.setProgress(85)
                return _write_coverage_outputs(
                    self, parameters, context, feedback, p, result,
                    dem_path, clutter_source, tx_clutter_for_report)
        finally:
            if clutter_grid is not None:
                with contextlib.suppress(Exception):
                    clutter_grid.close()
            self._tmp.cleanup()
            self._tmp.warn_persistent(feedback)

    def _apply_coverage_style(self, layer):
        from .coverage_palette import apply_coverage_style
        apply_coverage_style(layer)

    def _on_coverage_loaded(self, raster_layer):
        self._apply_coverage_style(raster_layer)
        raster_layer.setOpacity(1.0)
        self._coverage_layer_id = raster_layer.id()

    def name(self):
        return "coverage_analysis"

    def displayName(self):
        return self.tr("Coverage Analysis")

    def createInstance(self):
        return CoverageAlgorithm()


install_constants(CoverageAlgorithm, PARAM_CONSTANTS)
