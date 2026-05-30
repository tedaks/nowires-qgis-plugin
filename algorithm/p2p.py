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


Point-to-Point Radio Propagation Analysis Algorithm.

Computes ITM path loss, generates terrain profile with Fresnel zones,
and creates vector layers showing LOS, Fresnel zone, and terrain profile.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

from qgis.core import QgsProcessingException

from NoWires.base_algorithm import NoWiresAlgorithm, install_constants
from NoWires.constants import WGS84_CRS
from NoWires.radio import K_FACTOR_PRESETS, validate_itm_input_ranges, resolve_k_factor
from NoWires.antenna import antenna_config_from_values
from NoWires.p2p.params import (
    PARAM_CONSTANTS,
    add_p2p_params,
)
from NoWires.p2p.analysis_params import P2PAnalysisParams
from NoWires.p2p.compute import run_p2p_analysis
from NoWires.shared_params import extract_clutter_params, extract_link_budget_params


class P2PAlgorithm(NoWiresAlgorithm):
    """Point-to-point radio link analysis."""

    ALLOW_THREADING = True

    def __init__(self):
        super().__init__()
        self._p2p_post_processors = []
        self._pending_chart_kwargs = None

    def initAlgorithm(self, config):
        add_p2p_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        self._p2p_post_processors = []
        tx_point = self.parameterAsPoint(
            parameters, self.TX_POINT, context,
            crs=WGS84_CRS,
        )
        rx_point = self.parameterAsPoint(
            parameters, self.RX_POINT, context,
            crs=WGS84_CRS,
        )

        if tx_point is None or rx_point is None:
            raise QgsProcessingException("Both TX and RX points are required.")

        tx_lat = tx_point.y()
        tx_lon = tx_point.x()
        rx_lat = rx_point.y()
        rx_lon = rx_point.x()

        from NoWires.geo_bounds import validate_coordinates
        validate_coordinates(tx_lat, tx_lon, "TX")
        validate_coordinates(rx_lat, rx_lon, "RX")

        tx_h = self.parameterAsDouble(parameters, self.TX_HEIGHT, context)
        rx_h = self.parameterAsDouble(parameters, self.RX_HEIGHT, context)
        f_mhz = self.parameterAsDouble(parameters, self.FREQ_MHZ, context)
        polarization = self.parameterAsEnum(parameters, self.POLARIZATION, context)
        climate = self.parameterAsEnum(parameters, self.CLIMATE, context)
        time_pct = self.parameterAsDouble(parameters, self.TIME_PCT, context)
        location_pct = self.parameterAsDouble(parameters, self.LOCATION_PCT, context)
        situation_pct = self.parameterAsDouble(parameters, self.SITUATION_PCT, context)
        lb = extract_link_budget_params(self, parameters, context)
        tx_power = lb.tx_power_dbm
        tx_gain = lb.tx_gain_dbi
        rx_gain = lb.rx_gain_dbi
        cable_loss = lb.cable_loss_db
        rx_sens = lb.rx_sensitivity_dbm
        preset_index = self.parameterAsEnum(parameters, self.K_FACTOR_PRESET, context)
        custom_k_factor = self.parameterAsDouble(parameters, self.K_FACTOR, context)
        k_factor = resolve_k_factor(
            has_preset=preset_index < len(K_FACTOR_PRESETS),
            has_custom=True,
            custom_value=custom_k_factor,
            preset_index=preset_index,
        )
        n0 = self.parameterAsDouble(parameters, self.N0, context)
        epsilon = self.parameterAsDouble(parameters, self.EPSILON, context)
        sigma = self.parameterAsDouble(parameters, self.SIGMA, context)
        try:
            validate_itm_input_ranges(
                tx_height_m=tx_h,
                rx_height_m=rx_h,
                frequency_mhz=f_mhz,
                surface_refractivity_n0=n0,
                earth_conductivity_sigma=sigma,
                climate=climate,
                time_pct=time_pct,
                location_pct=location_pct,
                situation_pct=situation_pct,
                k_factor=k_factor,
                epsilon=epsilon,
            )
        except ValueError as exc:
            raise QgsProcessingException(str(exc))

        tx_antenna_config = antenna_config_from_values(
            preset=self.parameterAsEnum(parameters, self.TX_ANTENNA_PRESET, context),
            azimuth_deg=self.parameterAsDouble(parameters, self.TX_ANTENNA_AZ, context),
            front_back_db=self.parameterAsDouble(parameters, self.TX_FRONT_BACK_DB, context),
            downtilt_deg=self.parameterAsDouble(parameters, self.TX_DOWNTILT_DEG, context),
            horizontal_pattern_path=self.parameterAsFile(parameters, self.TX_H_PATTERN, context),
            vertical_pattern_path=self.parameterAsFile(parameters, self.TX_V_PATTERN, context),
        )
        rx_antenna_config = antenna_config_from_values(
            preset=self.parameterAsEnum(parameters, self.RX_ANTENNA_PRESET, context),
            azimuth_deg=self.parameterAsDouble(parameters, self.RX_ANTENNA_AZ, context),
            front_back_db=self.parameterAsDouble(parameters, self.RX_FRONT_BACK_DB, context),
            downtilt_deg=self.parameterAsDouble(parameters, self.RX_DOWNTILT_DEG, context),
            horizontal_pattern_path=self.parameterAsFile(parameters, self.RX_H_PATTERN, context),
            vertical_pattern_path=self.parameterAsFile(parameters, self.RX_V_PATTERN, context),
        )
        c = extract_clutter_params(self, parameters, context)

        show_chart = self.parameterAsBool(parameters, self.SHOW_CHART, context)
        profile_dest = self.parameterAsOutputLayer(parameters, self.OUTPUT_PROFILE, context)
        fresnel_dest = self.parameterAsOutputLayer(parameters, self.OUTPUT_FRESNEL, context)
        markers_dest = self.parameterAsOutputLayer(parameters, self.OUTPUT_MARKERS, context)
        report_csv_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_CSV, context)
        report_json_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_JSON, context)
        report_html_path = self.parameterAsFileOutput(parameters, self.OUTPUT_REPORT_HTML, context)

        p2p_params = P2PAnalysisParams(
            tx_lat=tx_lat, tx_lon=tx_lon, rx_lat=rx_lat, rx_lon=rx_lon,
            tx_h=tx_h, rx_h=rx_h, f_mhz=f_mhz,
            polarization=polarization, climate=climate,
            time_pct=time_pct, location_pct=location_pct,
            situation_pct=situation_pct,
            tx_power=tx_power, tx_gain=tx_gain, rx_gain=rx_gain,
            cable_loss=cable_loss, rx_sens=rx_sens,
            k_factor=k_factor, n0=n0, epsilon=epsilon, sigma=sigma,
            tx_antenna_config=tx_antenna_config,
            rx_antenna_config=rx_antenna_config,
            clutter_enabled=c.enabled, clutter_grid=c.grid,
            tx_clutter_override=c.tx_override,
            rx_clutter_override=c.rx_override,
            clutter_model=c.model,
            cch_override_m=c.cch_override_m,
            clutter_percentile=c.percentile,
            street_width_m=c.street_width_m,
            bel_enabled=c.bel_enabled,
            bel_building_type=c.bel_building_type,
            bel_elevation_angle_deg=c.bel_elevation_angle_deg,
            profile_dest=profile_dest, fresnel_dest=fresnel_dest,
            markers_dest=markers_dest,
            report_csv_path=report_csv_path,
            report_json_path=report_json_path,
            report_html_path=report_html_path,
            show_chart=show_chart,
            context=context, feedback=feedback,
            output_profile=self.OUTPUT_PROFILE,
            output_fresnel=self.OUTPUT_FRESNEL,
            output_markers=self.OUTPUT_MARKERS,
            output_report_csv=self.OUTPUT_REPORT_CSV,
            output_report_json=self.OUTPUT_REPORT_JSON,
            output_report_html=self.OUTPUT_REPORT_HTML,
            post_processor_sink=self._p2p_post_processors,
        )
        # Clutter grid lifecycle: user-provided grids stay owned by the caller;
        # auto-downloaded grids are closed inside run_p2p_analysis's own finally.
        result = run_p2p_analysis(p2p_params)
        self._pending_chart_kwargs = p2p_params._pending_chart_kwargs
        return result

    def postProcessAlgorithm(self, context, feedback):
        chart_kwargs = self._pending_chart_kwargs
        if chart_kwargs is not None:
            from NoWires.p2p.chart import show_profile_chart
            try:
                show_profile_chart(**chart_kwargs)
            except Exception:
                pass
            self._pending_chart_kwargs = None
        return super().postProcessAlgorithm(context, feedback)

    def name(self):
        return "p2p_analysis"

    def displayName(self):
        return self.tr("Point-to-Point Analysis")

    def createInstance(self):
        return P2PAlgorithm()


install_constants(P2PAlgorithm, PARAM_CONSTANTS)
