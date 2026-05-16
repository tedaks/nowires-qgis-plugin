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

Coverage Comparison Algorithm.

Runs two coverage analyses side-by-side and produces a delta raster
showing the difference in path loss (Panel A - Panel B) in dB.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import logging
from qgis.core import QgsProcessingException
from .base_algorithm import NoWiresAlgorithm, install_constants
from .constants import DEGREE_PADDING
from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid
from .geo_bounds import coverage_bounds
from .comparison_params import (
    GRID_SIZE_PRESETS, DELTA_STYLE_OPTIONS,
    PANEL_A_CONSTANTS, PANEL_B_CONSTANTS, OUTPUT_CONSTANTS, make_panel_config)
from .comparison_add_params import add_panel_params, add_comparison_params
from .comparison_outputs import (
    write_coverage_raster, write_delta_raster,
    write_comparison_html_report, compute_delta_summary,
    load_comparison_layers)
from .clutter import ensure_clutter_grid_for_area
from .comparison_panel import run_panel_coverage
from .comparison_reporting import (
    build_panel_info, build_delta_info, report_comparison_results,
    validate_panels, resolve_output_paths)
from .temp_manager import TempDirManager

logger = logging.getLogger(__name__)


class CoverageComparisonAlgorithm(NoWiresAlgorithm):
    """Dual-panel coverage comparison with delta raster output."""

    ALLOW_THREADING = True

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []
        self._comparison_post_processors = []
        self._tmp = TempDirManager()

    def initAlgorithm(self, config):
        panel_config = make_panel_config()
        add_panel_params(self, "PANEL_A", panel_config)
        add_panel_params(self, "PANEL_B", panel_config)
        add_comparison_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem

        self._raster_layer_ids = []
        self._comparison_post_processors = []
        self._tmp = TempDirManager()
        crs4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        delta_style = DELTA_STYLE_OPTIONS[
            self.parameterAsEnum(parameters, self.DELTA_STYLE, context)]
        threshold_db = self.parameterAsDouble(parameters, self.DELTA_THRESHOLD_DB, context)
        output_dir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)

        tx_point_a = self.parameterAsPoint(parameters, self.PANEL_A_POINT, context, crs=crs4326)
        tx_point_b = self.parameterAsPoint(parameters, self.PANEL_B_POINT, context, crs=crs4326)
        radius_km_a = self.parameterAsDouble(parameters, self.PANEL_A_RADIUS_KM, context)
        radius_km_b = self.parameterAsDouble(parameters, self.PANEL_B_RADIUS_KM, context)
        tx_lat_a, tx_lon_a, tx_lat_b, tx_lon_b = validate_panels(
            tx_point_a, tx_point_b, radius_km_a, radius_km_b)

        radius_km = max(radius_km_a, radius_km_b)
        tx_lat_center = (tx_lat_a + tx_lat_b) / 2.0
        tx_lon_center = (tx_lon_a + tx_lon_b) / 2.0

        pad_deg = max(DEGREE_PADDING, radius_km / (111320.0 / 1000.0) * 0.1)
        south, north, west, east = coverage_bounds(
            tx_lat_center, tx_lon_center, radius_km, padding_deg=pad_deg)

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(2)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise QgsProcessingException("Failed to obtain DEM data for the coverage area.")

        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(5)
        shared_clutter_grid = None
        try:
            with ElevationGrid(dem_path) as elev:

                # Load clutter grid once and share between panels to ensure consistency.
                shared_clutter_grid = None
                panel_a_clutter_model_idx = self.parameterAsEnum(
                    parameters, self.PANEL_A_CLUTTER_MODEL, context)
                panel_b_clutter_model_idx = self.parameterAsEnum(
                    parameters, self.PANEL_B_CLUTTER_MODEL, context)
                panel_a_clutter_enabled = panel_a_clutter_model_idx > 0
                panel_b_clutter_enabled = panel_b_clutter_model_idx > 0
                if panel_a_clutter_enabled or panel_b_clutter_enabled:
                    shared_clutter_grid = ensure_clutter_grid_for_area(
                        south=south, north=north, west=west, east=east, feedback=feedback)

                feedback.pushInfo("=" * 50)
                feedback.pushInfo("Running Panel A coverage...")
                feedback.pushInfo("=" * 50)
                feedback.setProgress(10)
                panel_a = run_panel_coverage(
                    self, "PANEL_A", parameters, context, feedback, elev,
                    south, north, west, east, shared_clutter_grid=shared_clutter_grid)

                panel_result_a = panel_a["result"]
                if panel_result_a is None:
                    raise QgsProcessingException("Panel A coverage produced no valid pixels.")
                prx_grid_a = panel_result_a.prx_grid
                loss_grid_a = panel_result_a.loss_grid
                min_lat_a = panel_result_a.min_lat
                max_lat_a = panel_result_a.max_lat
                min_lon_a = panel_result_a.min_lon
                max_lon_a = panel_result_a.max_lon
                if prx_grid_a is None:
                    raise QgsProcessingException("Panel A coverage computation was cancelled.")

                feedback.pushInfo("=" * 50)
                feedback.pushInfo("Running Panel B coverage...")
                feedback.pushInfo("=" * 50)
                feedback.setProgress(45)
                panel_b = run_panel_coverage(
                    self, "PANEL_B", parameters, context, feedback, elev,
                    south, north, west, east, shared_clutter_grid=shared_clutter_grid)

                panel_result_b = panel_b["result"]
                if panel_result_b is None:
                    raise QgsProcessingException("Panel B coverage produced no valid pixels.")
                prx_grid_b = panel_result_b.prx_grid
                loss_grid_b = panel_result_b.loss_grid
                min_lat_b = panel_result_b.min_lat
                max_lat_b = panel_result_b.max_lat
                min_lon_b = panel_result_b.min_lon
                max_lon_b = panel_result_b.max_lon
                if prx_grid_b is None:
                    raise QgsProcessingException("Panel B coverage computation was cancelled.")
                if feedback and feedback.isCanceled():
                    return {}

                feedback.pushInfo("Computing delta raster...")
                feedback.setProgress(80)

                if prx_grid_a.shape != prx_grid_b.shape:
                    gs_a = GRID_SIZE_PRESETS[
                        self.parameterAsEnum(parameters, self.PANEL_A_GRID_SIZE, context)]
                    gs_b = GRID_SIZE_PRESETS[
                        self.parameterAsEnum(parameters, self.PANEL_B_GRID_SIZE, context)]
                    raise QgsProcessingException(
                        "Panel A grid size ({}) and Panel B grid size ({}) "
                        "must match.".format(gs_a, gs_b))

                ds = compute_delta_summary(loss_grid_a, loss_grid_b, threshold_db)
                loss_delta_grid = ds["loss_delta_grid"]
                valid_count = ds["valid_count"]
                total_count = ds["total_count"]

                output_a_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_A, context)
                output_b_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_B, context)
                output_delta_path = self.parameterAsOutputLayer(
                    parameters, self.OUTPUT_DELTA, context)
                output_report_path = self.parameterAsFileOutput(
                    parameters, self.OUTPUT_REPORT_HTML, context)

                (output_a_path, output_b_path,
                 output_delta_path, output_report_path, _comp_tmpdir) = \
                    resolve_output_paths(
                        output_dir, output_a_path, output_b_path,
                        output_delta_path, output_report_path, self._tmp)
                if _comp_tmpdir:
                    self._tmp.warn_persistent(feedback)

                write_coverage_raster(
                    output_a_path, prx_grid_a,
                    min_lat_a, max_lat_a, min_lon_a, max_lon_a)
                write_coverage_raster(
                    output_b_path, prx_grid_b,
                    min_lat_b, max_lat_b, min_lon_b, max_lon_b)
                write_delta_raster(
                    output_delta_path, loss_delta_grid,
                    min_lat_a, max_lat_a, min_lon_a, max_lon_a)

                self._raster_layer_ids, self._comparison_post_processors = load_comparison_layers(
                    context, output_a_path, output_b_path,
                    output_delta_path, threshold_db, delta_style, feedback)

                panel_a_info = build_panel_info(panel_a, prx_grid_a)
                panel_b_info = build_panel_info(panel_b, prx_grid_b)
                delta_info = build_delta_info(delta_style, threshold_db, ds)

                report_comparison_results(
                    feedback, valid_count, total_count, delta_info, threshold_db)

                if output_report_path:
                    from pathlib import Path
                    try:
                        write_comparison_html_report(
                            Path(output_report_path),
                            panel_a_info, panel_b_info, delta_info)
                    except OSError as exc:
                        feedback.pushWarning("Could not write comparison report: {}".format(exc))
                    else:
                        feedback.pushInfo(
                            "Comparison report written to: {}".format(output_report_path))

                feedback.setProgress(100)
                return {
                    self.OUTPUT_A: output_a_path,
                    self.OUTPUT_B: output_b_path,
                    self.OUTPUT_DELTA: output_delta_path,
                    self.OUTPUT_REPORT_HTML: output_report_path,
                }
        finally:
            if shared_clutter_grid is not None:
                shared_clutter_grid.close()
            self._tmp.cleanup()
            self._tmp.warn_persistent(feedback)

    def shortHelpString(self):
        return (
            "Run two coverage analyses side-by-side and produce a delta raster "
            "showing the difference in path loss (Panel A minus Panel B) in dB. "
            "Choose 'diverging' style for a continuous blue-white-red ramp, or "
            "'threshold' style to classify pixels as improved / unchanged / degraded."
        )

    def name(self):
        return "coverage_comparison"

    def displayName(self):
        return self.tr("Coverage Comparison")

    def createInstance(self):
        return CoverageComparisonAlgorithm()


install_constants(CoverageComparisonAlgorithm, PANEL_A_CONSTANTS)
install_constants(CoverageComparisonAlgorithm, PANEL_B_CONSTANTS)
install_constants(CoverageComparisonAlgorithm, OUTPUT_CONSTANTS)