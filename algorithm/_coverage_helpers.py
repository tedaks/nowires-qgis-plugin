# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Private helpers for the Coverage algorithm.

Extracted from algorithm/coverage.py to keep the algorithm class within the
300-line source-file cap and to give Phase 3's dataclass migration a stable
extraction point for further coverage-side logic.
"""
import os

from qgis.core import Qgis, QgsRasterLayer, QgsVectorLayer

from NoWires.algorithm._project_paths import _project_or_temp_dir
from NoWires.clutter import (
    clutter_source_label, compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area,
)
from NoWires.geo_bounds import aoi_padding_deg, coverage_bounds
from NoWires.processing_utils import queue_layer_for_loading, register_destination_layer
from NoWires.radio_coverage.coverage_grids import CoverageGrids
from NoWires.three_d import remember_nowires_3d_layers
from NoWires.radio_coverage.reporting import (
    build_coverage_report_payload_for_grid, report_coverage_results,
    write_coverage_geotiff,
)
from NoWires.report.export import write_report_csv, write_report_html, write_report_json
from NoWires.report.markers import write_single_marker


def _build_clutter_context(p, clutter_grid, elev):
    """Resolve clutter grid, source label, and per-pixel placeholder context."""
    from NoWires.clutter.context import build_initial_clutter_context
    clutter_grid_resolved = clutter_grid
    if clutter_grid_resolved is None and p.clutter_enabled:
        pad_deg = aoi_padding_deg(p.radius_km * 1000.0)
        south, north, west, east = coverage_bounds(
            p.tx_lat, p.tx_lon, p.radius_km, padding_deg=pad_deg)
        clutter_grid_resolved = ensure_clutter_grid_for_area(
            south=south, north=north, west=west, east=east)
    owns_grid = (clutter_grid_resolved is not None
                 and clutter_grid_resolved is not clutter_grid)
    try:
        clutter_source = clutter_source_label(
            enabled=p.clutter_enabled, land_cover_grid=clutter_grid_resolved,
            raster_path=p.clutter_raster_path,
            tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override)
        clutter_context = None
        if p.clutter_enabled:
            clutter_context = build_initial_clutter_context(
                frequency_mhz=p.f_mhz, tx_height_m=p.tx_h, rx_height_m=p.rx_h,
                cch_override_m=p.cch_override_m, model=p.clutter_model,
                percentile=p.clutter_percentile, street_width_m=p.street_width_m,
                bel_enabled=p.bel_enabled, bel_building_type=p.bel_building_type,
                bel_elevation_angle_deg=p.bel_elevation_angle_deg)
        tx_clutter_for_report = compute_terminal_clutter_losses(
            tx_lat=p.tx_lat, tx_lon=p.tx_lon, rx_lat=p.tx_lat, rx_lon=p.tx_lon,
            frequency_mhz=p.f_mhz, enabled=p.clutter_enabled,
            land_cover_grid=clutter_grid_resolved,
            tx_override=p.tx_clutter_override, rx_override=p.rx_clutter_override,
            context=clutter_context)
    except Exception:
        if owns_grid:
            try:
                clutter_grid_resolved.close()
            except Exception:
                pass
        raise
    return clutter_grid_resolved, clutter_context, clutter_source, tx_clutter_for_report, owns_grid


def _write_coverage_outputs(algorithm, parameters, context, feedback, p, result,
                            dem_path, clutter_source, tx_clutter_for_report):
    """Write coverage raster, reports, and load QGIS layers."""
    tif_path = algorithm.parameterAsOutputLayer(parameters, algorithm.OUTPUT_RASTER, context)
    coverage_dir = None
    if not tif_path:
        coverage_dir = _project_or_temp_dir(
            algorithm._tmp, context, feedback, "coverage_prx")
        tif_path = os.path.join(coverage_dir, "coverage_prx.tif")
    report_csv_path = algorithm.parameterAsFileOutput(parameters, algorithm.OUTPUT_REPORT_CSV, context)
    report_json_path = algorithm.parameterAsFileOutput(parameters, algorithm.OUTPUT_REPORT_JSON, context)
    report_html_path = algorithm.parameterAsFileOutput(parameters, algorithm.OUTPUT_REPORT_HTML, context)
    report_pdf_path = algorithm.parameterAsFileOutput(parameters, algorithm.OUTPUT_REPORT_PDF, context)

    report_payload, raster_grid, valid, summary = (
        build_coverage_report_payload_for_grid(
            grids=CoverageGrids(
                prx_grid=result.prx_grid, loss_grid=result.loss_grid,
                itm_loss_grid=result.itm_loss_grid,
                clutter_loss_grid=result.clutter_loss_grid,
                clutter_rx_db_grid=result.clutter_rx_db_grid,
                bel_rx_db_grid=result.bel_rx_db_grid,
                min_lat=result.min_lat, max_lat=result.max_lat,
                min_lon=result.min_lon, max_lon=result.max_lon),
            params=p,
            clutter_source=clutter_source,
            tx_clutter_for_report=tx_clutter_for_report,
            extra_inputs={
                "n0": p.n0, "epsilon": p.epsilon, "sigma": p.sigma,
                "antenna_az": p.antenna_az, "antenna_bw_override": p.antenna_bw_override,
                "downtilt_deg": p.downtilt_deg, "front_back_db": p.front_back_db,
                "cch_override_m": p.cch_override_m, "clutter_percentile": p.clutter_percentile,
                "street_width_m": p.street_width_m,
                "bel_enabled": p.bel_enabled, "bel_building_type": p.bel_building_type,
                "bel_elevation_angle_deg": p.bel_elevation_angle_deg,
            },
        ))

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
        # Defer legend.show() — Cocoa rejects QWidget creation off main thread.
        algorithm._pending_legend_rx_sens = p.rx_sens
        marker_dir = coverage_dir or _project_or_temp_dir(
            algorithm._tmp, context, feedback, "coverage_prx")
        markers_path = os.path.join(marker_dir, "tx_marker.gpkg")
        write_single_marker(markers_path, lat=p.tx_lat, lon=p.tx_lon, height_m=p.tx_h,
                            gain_dbi=p.tx_gain, power_dbm=p.tx_power, label="TX")
        tx_layer = QgsVectorLayer(markers_path, "Coverage TX")
        if tx_layer.isValid():
            queue_layer_for_loading(context, tx_layer, "Coverage TX")
            algorithm._vector_layer_ids.append(tx_layer.id())
        remember_nowires_3d_layers(
            context.project(), dem_layer=dem_layer, coverage_layer=raster_layer)
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
    if report_pdf_path:
        from NoWires.report.pdf import write_report_pdf
        if not write_report_pdf(report_pdf_path, report_payload, "NoWires Coverage Report"):
            feedback.pushWarning("PDF report skipped — Qt print-support unavailable.")
    return {
        algorithm.OUTPUT_RASTER: tif_path,
        algorithm.OUTPUT_REPORT_CSV: report_csv_path,
        algorithm.OUTPUT_REPORT_JSON: report_json_path,
        algorithm.OUTPUT_REPORT_HTML: report_html_path,
        algorithm.OUTPUT_REPORT_PDF: report_pdf_path,
    }
