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


Coverage Comparison Algorithm.

Runs two coverage analyses side-by-side and produces a delta raster
showing the difference in path loss (Panel A - Panel B) in dB.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import logging
import math
import os
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsRasterLayer,
)

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid
from .processing_utils import queue_layer_for_loading

from .comparison_params import (
    GRID_SIZE_PRESETS,
    DELTA_STYLE_OPTIONS,
    METERS_PER_DEGREE_LAT,
    PANEL_A_CONSTANTS,
    PANEL_B_CONSTANTS,
    OUTPUT_CONSTANTS,
    make_panel_config,
)
from .comparison_add_params import add_panel_params, add_comparison_params
from .comparison_outputs import (
    write_coverage_raster,
    write_delta_raster,
    apply_delta_style,
    write_comparison_html_report,
    compute_delta_summary,
)
from .comparison_panel import run_panel_coverage


def _install_constants(cls, constants_dict):
    for key, value in constants_dict.items():
        setattr(cls, key, value)


class CoverageComparisonAlgorithm(QgsProcessingAlgorithm):
    """Dual-panel coverage comparison with delta raster output."""

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        panel_config = make_panel_config()
        add_panel_params(self, "PANEL_A", panel_config)
        add_panel_params(self, "PANEL_B", panel_config)
        add_comparison_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        self._raster_layer_ids = []
        from qgis.core import QgsCoordinateReferenceSystem

        output_dir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)
        delta_style_index = self.parameterAsEnum(parameters, self.DELTA_STYLE, context)
        delta_style = DELTA_STYLE_OPTIONS[delta_style_index]
        threshold_db = self.parameterAsDouble(parameters, self.DELTA_THRESHOLD_DB, context)

        tx_point_a = self.parameterAsPoint(
            parameters, self.PANEL_A_POINT, context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        if tx_point_a is None:
            raise ValueError("Panel A TX point is required.")
        tx_lat_a = tx_point_a.y()
        tx_lon_a = tx_point_a.x()
        radius_km_a = self.parameterAsDouble(parameters, self.PANEL_A_RADIUS_KM, context)

        tx_point_b = self.parameterAsPoint(
            parameters, self.PANEL_B_POINT, context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        if tx_point_b is None:
            raise ValueError("Panel B TX point is required.")
        tx_lat_b = tx_point_b.y()
        tx_lon_b = tx_point_b.x()
        radius_km_b = self.parameterAsDouble(parameters, self.PANEL_B_RADIUS_KM, context)

        if (abs(tx_lat_a - tx_lat_b) > 1e-9 or abs(tx_lon_a - tx_lon_b) > 1e-9):
            raise QgsProcessingException(
                "Panel A and B TX positions differ. "
                "Delta comparison requires co-located transmitters."
            )
        if abs(radius_km_a - radius_km_b) > 1e-9:
            raise QgsProcessingException(
                "Panel A and B radii differ. "
                "Delta comparison requires identical analysis radii."
            )

        radius_km = max(radius_km_a, radius_km_b)
        tx_lat_center = (tx_lat_a + tx_lat_b) / 2.0
        tx_lon_center = (tx_lon_a + tx_lon_b) / 2.0

        pad_deg = max(0.05, radius_km / (METERS_PER_DEGREE_LAT / 1000.0) * 0.1)
        radius_deg_lat = radius_km / (METERS_PER_DEGREE_LAT / 1000.0)
        radius_deg_lon = radius_km / (
            METERS_PER_DEGREE_LAT / 1000.0 * max(math.cos(math.radians(tx_lat_center)), 0.01)
        )
        south = tx_lat_center - radius_deg_lat - pad_deg
        north = tx_lat_center + radius_deg_lat + pad_deg
        west = tx_lon_center - radius_deg_lon - pad_deg
        east = tx_lon_center + radius_deg_lon + pad_deg

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(2)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise RuntimeError("Failed to obtain DEM data for the coverage area.")

        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(5)
        elev = ElevationGrid(dem_path)

        feedback.pushInfo("=" * 50)
        feedback.pushInfo("Running Panel A coverage...")
        feedback.pushInfo("=" * 50)
        feedback.setProgress(10)
        panel_a = run_panel_coverage(
            self, "PANEL_A", parameters, context, feedback, elev, south, north, west, east
        )

        (
            prx_grid_a,
            loss_grid_a,
            min_lat_a,
            max_lat_a,
            min_lon_a,
            max_lon_a,
            itm_loss_grid_a,
            clutter_loss_grid_a,
        ) = panel_a["result"]

        if prx_grid_a is None:
            raise RuntimeError("Panel A coverage computation was cancelled.")

        if feedback and feedback.isCanceled():
            return {}

        feedback.pushInfo("=" * 50)
        feedback.pushInfo("Running Panel B coverage...")
        feedback.pushInfo("=" * 50)
        feedback.setProgress(45)
        panel_b = run_panel_coverage(
            self, "PANEL_B", parameters, context, feedback, elev, south, north, west, east
        )

        (
            prx_grid_b,
            loss_grid_b,
            min_lat_b,
            max_lat_b,
            min_lon_b,
            max_lon_b,
            itm_loss_grid_b,
            clutter_loss_grid_b,
        ) = panel_b["result"]

        if prx_grid_b is None:
            raise RuntimeError("Panel B coverage computation was cancelled.")

        tx_lat_a = panel_a["tx_lat"]
        tx_lon_a = panel_a["tx_lon"]
        tx_lat_b = panel_b["tx_lat"]
        tx_lon_b = panel_b["tx_lon"]
        radius_km_a = panel_a["radius_km"]
        radius_km_b = panel_b["radius_km"]

        feedback.pushInfo("Computing delta raster...")
        feedback.setProgress(80)

        if prx_grid_a.shape != prx_grid_b.shape:
            grid_size_a_val = GRID_SIZE_PRESETS[self.parameterAsEnum(parameters, self.PANEL_A_GRID_SIZE, context)]
            grid_size_b_val = GRID_SIZE_PRESETS[self.parameterAsEnum(parameters, self.PANEL_B_GRID_SIZE, context)]
            raise ValueError(
                "Panel A grid size ({}) and Panel B grid size ({}) must match. "
                "Set both panels to the same grid size resolution.".format(
                    grid_size_a_val, grid_size_b_val
                )
            )

        ds = compute_delta_summary(loss_grid_a, loss_grid_b, threshold_db)
        loss_delta_grid = ds["loss_delta_grid"]
        valid_mask = ds["valid_mask"]
        valid_count = ds["valid_count"]
        total_count = ds["total_count"]
        improved = ds["improved"]
        degraded = ds["degraded"]
        unchanged = ds["unchanged"]
        min_delta = ds["min_delta"]
        max_delta = ds["max_delta"]
        mean_delta = ds["mean_delta"]

        output_a_path = self.parameterAsFileOutput(parameters, self.OUTPUT_A, context)
        output_b_path = self.parameterAsFileOutput(parameters, self.OUTPUT_B, context)
        output_delta_path = self.parameterAsFileOutput(parameters, self.OUTPUT_DELTA, context)
        output_report_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_HTML, context)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_a_path = output_a_path or os.path.join(output_dir, "coverage_a.tif")
            output_b_path = output_b_path or os.path.join(output_dir, "coverage_b.tif")
            output_delta_path = output_delta_path or os.path.join(output_dir, "coverage_delta.tif")
            output_report_path = output_report_path or os.path.join(output_dir, "comparison_report.html")

        _comp_tmpdir = None
        if not output_a_path or not output_b_path or not output_delta_path:
            _comp_tmpdir = tempfile.mkdtemp(prefix="nowires_comp_")
            feedback.pushInfo(
                "Temporary raster outputs are intentionally left on disk for QGIS layer loading: {}".format(
                    _comp_tmpdir
                )
            )
        if not output_a_path:
            output_a_path = os.path.join(_comp_tmpdir, "coverage_a.tif")
        if not output_b_path:
            output_b_path = os.path.join(_comp_tmpdir, "coverage_b.tif")
        if not output_delta_path:
            output_delta_path = os.path.join(_comp_tmpdir, "coverage_delta.tif")

        write_coverage_raster(output_a_path, prx_grid_a, min_lat_a, max_lat_a, min_lon_a, max_lon_a, panel_a["rx_sens"])
        write_coverage_raster(output_b_path, prx_grid_b, min_lat_b, max_lat_b, min_lon_b, max_lon_b, panel_b["rx_sens"])

        write_delta_raster(output_delta_path, loss_delta_grid, min_lat_a, max_lat_a, min_lon_a, max_lon_a)

        layer_delta = QgsRasterLayer(output_delta_path, "Coverage Delta (A - B dB)")
        if layer_delta.isValid():
            apply_delta_style(layer_delta, threshold_db, style=delta_style)
            queue_layer_for_loading(context, layer_delta, "Coverage Delta (A - B dB)")
            self._raster_layer_ids.append(layer_delta.id())

        layer_a = QgsRasterLayer(output_a_path, "Coverage Panel A")
        if layer_a.isValid():
            from .coverage_palette import apply_coverage_style
            apply_coverage_style(layer_a)
            queue_layer_for_loading(context, layer_a, "Coverage Panel A")
            self._raster_layer_ids.append(layer_a.id())

        layer_b = QgsRasterLayer(output_b_path, "Coverage Panel B")
        if layer_b.isValid():
            from .coverage_palette import apply_coverage_style as _apply_cov_b
            _apply_cov_b(layer_b)
            queue_layer_for_loading(context, layer_b, "Coverage Panel B")
            self._raster_layer_ids.append(layer_b.id())

        panel_a_info = {
            "tx_lat": panel_a["tx_lat"], "tx_lon": panel_a["tx_lon"], "tx_h": panel_a["tx_h"], "rx_h": panel_a["rx_h"],
            "f_mhz": panel_a["f_mhz"], "radius_km": panel_a["radius_km"], "tx_power": panel_a["tx_power"],
            "tx_gain": panel_a["tx_gain"], "rx_gain": panel_a["rx_gain"], "cable_loss": panel_a["cable_loss"],
            "valid_pixels": int((~np.isnan(prx_grid_a)).sum()),
            "total_pixels": int(prx_grid_a.size),
            "mean_prx": float(np.nanmean(prx_grid_a)) if np.any(~np.isnan(prx_grid_a)) else float('nan'),
        }
        panel_b_info = {
            "tx_lat": panel_b["tx_lat"], "tx_lon": panel_b["tx_lon"], "tx_h": panel_b["tx_h"], "rx_h": panel_b["rx_h"],
            "f_mhz": panel_b["f_mhz"], "radius_km": panel_b["radius_km"], "tx_power": panel_b["tx_power"],
            "tx_gain": panel_b["tx_gain"], "rx_gain": panel_b["rx_gain"], "cable_loss": panel_b["cable_loss"],
            "valid_pixels": int((~np.isnan(prx_grid_b)).sum()),
            "total_pixels": int(prx_grid_b.size),
            "mean_prx": float(np.nanmean(prx_grid_b)) if np.any(~np.isnan(prx_grid_b)) else float('nan'),
        }
        delta_info = {
            "style": delta_style,
            "threshold_db": threshold_db,
            "valid_pixels": valid_count,
            "improved_pixels": improved,
            "improved_pct": improved / max(valid_count, 1) * 100,
            "degraded_pixels": degraded,
            "degraded_pct": degraded / max(valid_count, 1) * 100,
            "unchanged_pixels": unchanged,
            "unchanged_pct": unchanged / max(valid_count, 1) * 100,
            "min_delta": min_delta,
            "max_delta": max_delta,
            "mean_delta": mean_delta,
        }

        feedback.pushInfo("")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo("COVERAGE COMPARISON RESULTS")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo(f"Valid delta pixels: {valid_count} / {total_count}")
        feedback.pushInfo(f"Improved (A better, <-{threshold_db:.1f} dB): {improved} ({delta_info['improved_pct']:.1f}%)")
        feedback.pushInfo(f"Degraded (A worse, >+{threshold_db:.1f} dB): {degraded} ({delta_info['degraded_pct']:.1f}%)")
        feedback.pushInfo(f"Unchanged (within threshold): {unchanged} ({delta_info['unchanged_pct']:.1f}%)")
        feedback.pushInfo(f"Delta range: {min_delta:.2f} to {max_delta:.2f} dB (mean: {mean_delta:.2f} dB)")
        feedback.pushInfo("=" * 50)

        if output_report_path:
            from pathlib import Path
            try:
                write_comparison_html_report(Path(output_report_path), panel_a_info, panel_b_info, delta_info)
            except OSError as exc:
                feedback.pushWarning("Could not write comparison report: {}".format(exc))
            else:
                feedback.pushInfo(f"Comparison report written to: {output_report_path}")

        try:
            feedback.setProgress(100)
            return {
                self.OUTPUT_A: output_a_path,
                self.OUTPUT_B: output_b_path,
                self.OUTPUT_DELTA: output_delta_path,
                self.OUTPUT_REPORT_HTML: output_report_path,
            }
        finally:
            if _comp_tmpdir and os.path.isdir(_comp_tmpdir):
                pass

    def postProcessAlgorithm(self, context, feedback):
        from qgis.core import QgsProject
        root = QgsProject.instance().layerTreeRoot()
        for layer_id in self._raster_layer_ids:
            node = root.findLayer(layer_id)
            if node is not None:
                clone = node.clone()
                parent = node.parent()
                parent.removeChildNode(node)
                parent.insertChildNode(0, clone)
        return {}

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

    def group(self):
        return self.tr("Radio Propagation")

    def groupId(self):
        return "radio_propagation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return CoverageComparisonAlgorithm()


_install_constants(CoverageComparisonAlgorithm, PANEL_A_CONSTANTS)
_install_constants(CoverageComparisonAlgorithm, PANEL_B_CONSTANTS)
_install_constants(CoverageComparisonAlgorithm, OUTPUT_CONSTANTS)