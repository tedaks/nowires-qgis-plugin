# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coverage Analysis Algorithm — heatmap prediction via ITM."""
import contextlib

from qgis.core import QgsProcessingException
from NoWires.base_algorithm import NoWiresAlgorithm, install_constants
from NoWires.dem_downloader import ensure_dem_for_area
from NoWires.elevation import ElevationGrid
from NoWires.radio_coverage.legend import show_coverage_legend
from NoWires.radio_coverage.compute import DEFAULT_MAX_PROFILE_PTS, coverage_profile_step_m
from NoWires.radio_coverage.dem_validate import validate_dem_coverage
from NoWires.radio_coverage.engine import compute_coverage
from NoWires.clutter import CLUTTER_MODEL_OPTIONS
from NoWires.radio_coverage.params import PARAM_CONSTANTS, add_coverage_params, extract_coverage_params
from NoWires.antenna import ANTENNA_PRESET_OPTIONS
from NoWires.geo_bounds import aoi_padding_deg, coverage_bounds
from NoWires.shared_params import warn_if_omni_preset_discards_directional
from NoWires.temp_manager import TempDirManager
from NoWires.algorithm._coverage_helpers import (
    _build_clutter_context, _write_coverage_outputs,
)


class CoverageAlgorithm(NoWiresAlgorithm):
    """Coverage analysis heatmap prediction."""

    ALLOW_THREADING = True

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []
        self._vector_layer_ids = []
        self._coverage_post_processor = None
        self._coverage_layer_id = None

    def initAlgorithm(self, config):
        add_coverage_params(self)

    def postProcessAlgorithm(self, context, feedback):
        rx = getattr(self, "_pending_legend_rx_sens", None)
        if rx is not None:  # main thread — safe to .show() (Cocoa-required)
            show_coverage_legend(rx_sensitivity_dbm=rx)
            self._pending_legend_rx_sens = None
        return super().postProcessAlgorithm(context, feedback)

    def processAlgorithm(self, parameters, context, feedback):
        self._raster_layer_ids = []
        self._vector_layer_ids = []
        self._coverage_post_processor = None
        self._pending_legend_rx_sens = None
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
        warn_if_omni_preset_discards_directional(
            feedback, antenna_preset=p.antenna_preset,
            antenna_bw_override=p.antenna_bw_override, downtilt_deg=p.downtilt_deg)

        pad_deg = aoi_padding_deg(p.radius_km * 1000.0)
        south, north, west, east = coverage_bounds(
            p.tx_lat, p.tx_lon, p.radius_km, padding_deg=pad_deg)

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise QgsProcessingException("Failed to obtain DEM data for the coverage area.")

        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(15)
        _owns_clutter = False
        try:
            with ElevationGrid(dem_path) as elev:
                validate_dem_coverage(elev, south, north, west, east, feedback)
                clutter_grid, clutter_context, clutter_source, tx_clutter_for_report, \
                    _owns_clutter = _build_clutter_context(p, p.clutter_grid, elev)
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
                    clutter_context=clutter_context,
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
            # Only close auto-downloaded clutter grids; user-provided
            # grids are owned by the caller and must not be closed here.
            if _owns_clutter and clutter_grid is not None:
                with contextlib.suppress(Exception):
                    clutter_grid.close()
            self._tmp.cleanup()
            self._tmp.warn_persistent(feedback)

    def _on_coverage_loaded(self, layer):
        from NoWires.radio_coverage.palette import apply_coverage_style
        apply_coverage_style(layer)
        layer.setOpacity(1.0)
        self._coverage_layer_id = layer.id()

    def name(self):
        return "coverage_analysis"

    def displayName(self):
        return self.tr("Coverage Analysis")

    def createInstance(self):
        return CoverageAlgorithm()

install_constants(CoverageAlgorithm, PARAM_CONSTANTS)
