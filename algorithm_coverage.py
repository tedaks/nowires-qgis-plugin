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


Coverage Analysis Algorithm — heatmap prediction via ITM.
"""

import logging
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
from .coverage_params import (
    PARAM_CONSTANTS, add_coverage_params, extract_coverage_params,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .constants import DEGREE_PADDING
from .geo_bounds import coverage_bounds
from .coverage_reporting import (
    build_coverage_report_payload_for_grid, report_coverage_results,
    write_coverage_geotiff,
)
from .processing_utils import queue_layer_for_loading
from .temp_manager import TempDirManager


class CoverageAlgorithm(NoWiresAlgorithm):
    """Coverage analysis heatmap prediction."""

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []

    def initAlgorithm(self, config):
        add_coverage_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        self._raster_layer_ids = []
        self._tmp = TempDirManager()
        clutter_grid = None
        p = extract_coverage_params(self, parameters, context)

        feedback.pushInfo(
            "TX: ({:.5f}, {:.5f}), F={:.1f} MHz, R={:.1f} km, Grid={}x{}".format(
                p.tx_lat, p.tx_lon, p.f_mhz,
                p.radius_km, p.grid_size, p.grid_size))
        feedback.pushInfo("Clutter correction: {}".format(
            CLUTTER_MODEL_OPTIONS[2] if p.clutter_enabled and p.clutter_model == "advanced"
            else CLUTTER_MODEL_OPTIONS[1] if p.clutter_enabled else CLUTTER_MODEL_OPTIONS[0]))
        feedback.pushInfo("TX antenna preset: {}".format(
            ANTENNA_PRESET_OPTIONS[p.antenna_preset]))

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
                clutter_grid = p.clutter_grid
                if clutter_grid is None and p.clutter_enabled:
                    clutter_grid = ensure_clutter_grid_for_area(
                        south=south, north=north, west=west, east=east, feedback=feedback)
                clutter_source = clutter_source_label(
                    enabled=p.clutter_enabled, land_cover_grid=clutter_grid,
                    raster_path=p.clutter_raster_path,
                    tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override)
                clutter_context = None
                if p.clutter_enabled:
                    from .clutter_context import ClutterLossContext
                    clutter_context = ClutterLossContext(
                        frequency_mhz=p.f_mhz, distance_m=0.0,
                        tx_height_m=p.tx_h, rx_height_m=p.rx_h,
                        rx_ground_elevation_m=0.0, polarization=p.polarization,
                        cch_override_m=p.cch_override_m, model=p.clutter_model,
                    )
                tx_clutter_for_report = compute_terminal_clutter_losses(
                    tx_lat=p.tx_lat, tx_lon=p.tx_lon, rx_lat=p.tx_lat,
                    rx_lon=p.tx_lon, frequency_mhz=p.f_mhz,
                    enabled=p.clutter_enabled, land_cover_grid=clutter_grid,
                    tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override,
                    context=clutter_context)

                feedback.pushInfo("Computing coverage...")
                feedback.setProgress(20)

                result = compute_coverage(
                    elev_grid=elev,
                    tx_lat=p.tx_lat, tx_lon=p.tx_lon,
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
                    clutter_model=p.clutter_model,
                    cch_override_m=p.cch_override_m,
                    feedback=feedback)

                if result is None or result.prx_grid is None:
                    raise QgsProcessingException("Coverage computation was cancelled.")

                report_payload, raster_grid, valid, summary = (
                    build_coverage_report_payload_for_grid(
                        prx_grid=result.prx_grid, loss_grid=result.loss_grid,
                        itm_loss_grid=result.itm_loss_grid,
                        clutter_loss_grid=result.clutter_loss_grid,
                        min_lat=result.min_lat, max_lat=result.max_lat,
                        min_lon=result.min_lon, max_lon=result.max_lon,
                        tx_lat=p.tx_lat, tx_lon=p.tx_lon, tx_h=p.tx_h, rx_h=p.rx_h,
                        f_mhz=p.f_mhz, radius_km=p.radius_km, grid_size=p.grid_size,
                        polarization=p.polarization, climate=p.climate,
                        time_pct=p.time_pct, location_pct=p.location_pct,
                        situation_pct=p.situation_pct, tx_power=p.tx_power,
                        tx_gain=p.tx_gain, rx_gain=p.rx_gain, cable_loss=p.cable_loss,
                        rx_sens=p.rx_sens, clutter_enabled=p.clutter_enabled,
                        clutter_model=p.clutter_model,
                        antenna_preset=p.antenna_preset,
                        clutter_source=clutter_source,
                        tx_clutter_for_report=tx_clutter_for_report))

                feedback.pushInfo("Writing coverage raster...")
                feedback.setProgress(85)

                tif_dest = self.parameterAsFileOutput(parameters, self.OUTPUT_RASTER, context)
                tif_path = tif_dest
                if not tif_path:
                    coverage_tmpdir = self._tmp.make_dir("coverage_prx", persistent=True)
                    tif_path = os.path.join(coverage_tmpdir, "coverage_prx.tif")
                    self._tmp.warn_persistent(feedback)
                report_csv_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_CSV, context)
                report_json_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_JSON, context)
                report_html_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_HTML, context)

                write_coverage_geotiff(result.prx_grid, result.min_lat, result.max_lat, result.min_lon, result.max_lon, tif_path)

                layer_name = "Coverage ({:.0f} MHz, {:.0f} km, {}x{})".format(
                    p.f_mhz, p.radius_km, p.grid_size, p.grid_size)
                raster_layer = QgsRasterLayer(tif_path, layer_name)

                if raster_layer.isValid():
                    self._apply_coverage_style(raster_layer)
                    raster_layer.setOpacity(1.0)

                    dem_layer = QgsRasterLayer(dem_path, "NoWires DEM (GLO-30)")
                    if dem_layer.isValid():
                        elev_props = dem_layer.elevationProperties()
                        elev_props.setEnabled(True)
                        elev_props.setMode(Qgis.RasterElevationMode.RepresentsElevationSurface)
                        elev_props.setBandNumber(1)
                        queue_layer_for_loading(context, dem_layer, "NoWires DEM (GLO-30)")
                        self._raster_layer_ids.append(dem_layer.id())
                        self._dem_layer_id = dem_layer.id()

                    queue_layer_for_loading(context, raster_layer, layer_name)
                    self._coverage_layer_id = raster_layer.id()
                    show_coverage_legend(rx_sensitivity_dbm=p.rx_sens)
                else:
                    feedback.pushWarning("Could not load coverage raster layer: {}".format(raster_layer.error().summary()))

                report_coverage_results(
                    feedback, report_payload, raster_grid, valid, p.rx_sens,
                    summary=summary)
                if report_csv_path:
                    write_report_csv(report_csv_path, report_payload)
                if report_json_path:
                    write_report_json(report_json_path, report_payload)
                if report_html_path:
                    write_report_html(
                        report_html_path, report_payload,
                        title="NoWires Coverage Report")

                feedback.setProgress(100)
                return {
                    self.OUTPUT_RASTER: tif_path,
                    self.OUTPUT_REPORT_CSV: report_csv_path,
                    self.OUTPUT_REPORT_JSON: report_json_path,
                    self.OUTPUT_REPORT_HTML: report_html_path,
                }
        finally:
            if clutter_grid is not None:
                clutter_grid.close()
            self._tmp.cleanup()
            self._tmp.warn_persistent(feedback)

    def _apply_coverage_style(self, layer):
        """Apply a color ramp renderer based on signal level thresholds."""
        from .coverage_palette import apply_coverage_style
        apply_coverage_style(layer)

    def name(self):
        return "coverage_analysis"

    def displayName(self):
        return self.tr("Coverage Analysis")

    def createInstance(self):
        return CoverageAlgorithm()


install_constants(CoverageAlgorithm, PARAM_CONSTANTS)
