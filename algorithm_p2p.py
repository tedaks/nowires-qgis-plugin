# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2024 Bortre Tenamo
                               Adaptations (C) 2026 by Bortre Tenamo
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

import logging
import math
import os
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProject,
    QgsProcessingContext,
    QgsVectorLayer,
)
from osgeo import ogr, osr

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid, haversine_m
from .qt_compat import (
    dock_widget_area_right,
    matplotlib_qt_backend,
    widget_attribute_delete_on_close,
)
from .radio import (
    CLIMATE_NAMES,
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_N0,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MIN_SIGMA,
    ITM_MIN_TERMINAL_HEIGHT_M,
    K_FACTOR_PRESETS,
    PROP_MODE_NAMES,
    SIGNAL_LEVELS,
    build_pfl,
    fresnel_profile_analysis,
    itm_p2p_loss,
    resolve_k_factor,
    validate_itm_input_ranges,
)
from .report_export import write_report_csv, write_report_html, write_report_json
from .report_payloads import (
    build_p2p_report_payload,
    ogr_driver_for_path,
    _remove_existing_ogr_dataset,
    write_p2p_marker_layer,
)

POLARIZATION_NAMES = {0: "Horizontal", 1: "Vertical"}


def _queue_layer_for_loading(context, layer, name):
    """Hand a layer to Processing for loading instead of mutating the project."""
    if layer is None or not layer.isValid():
        return False
    if not (
        hasattr(context, "temporaryLayerStore")
        and hasattr(context, "addLayerToLoadOnCompletion")
    ):
        return False
    project = QgsProject.instance()
    context.temporaryLayerStore().addMapLayer(layer)
    context.addLayerToLoadOnCompletion(
        layer.id(), QgsProcessingContext.LayerDetails(name, project, name)
    )
    return True


class P2PAlgorithm(QgsProcessingAlgorithm):
    """Point-to-point radio link analysis."""

    TX_POINT = "TX_POINT"
    RX_POINT = "RX_POINT"
    TX_HEIGHT = "TX_HEIGHT"
    RX_HEIGHT = "RX_HEIGHT"
    FREQ_MHZ = "FREQ_MHZ"
    POLARIZATION = "POLARIZATION"
    CLIMATE = "CLIMATE"
    TIME_PCT = "TIME_PCT"
    LOCATION_PCT = "LOCATION_PCT"
    SITUATION_PCT = "SITUATION_PCT"
    TX_POWER = "TX_POWER"
    TX_GAIN = "TX_GAIN"
    RX_GAIN = "RX_GAIN"
    CABLE_LOSS = "CABLE_LOSS"
    RX_SENSITIVITY = "RX_SENSITIVITY"
    K_FACTOR_PRESET = "K_FACTOR_PRESET"
    K_FACTOR = "K_FACTOR"
    N0 = "N0"
    EPSILON = "EPSILON"
    SIGMA = "SIGMA"
    OUTPUT_PROFILE = "OUTPUT_PROFILE"
    OUTPUT_FRESNEL = "OUTPUT_FRESNEL"
    OUTPUT_MARKERS = "OUTPUT_MARKERS"
    OUTPUT_REPORT_CSV = "OUTPUT_REPORT_CSV"
    OUTPUT_REPORT_JSON = "OUTPUT_REPORT_JSON"
    OUTPUT_REPORT_HTML = "OUTPUT_REPORT_HTML"
    SHOW_CHART = "SHOW_CHART"

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterPoint(self.TX_POINT, "Transmitter (TX) point")
        )
        self.addParameter(
            QgsProcessingParameterPoint(self.RX_POINT, "Receiver (RX) point")
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_HEIGHT,
                "TX antenna height (m)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=30.0,
                minValue=ITM_MIN_TERMINAL_HEIGHT_M,
                maxValue=ITM_MAX_TERMINAL_HEIGHT_M,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_HEIGHT,
                "RX antenna height (m)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=ITM_MIN_TERMINAL_HEIGHT_M,
                maxValue=ITM_MAX_TERMINAL_HEIGHT_M,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.FREQ_MHZ,
                "Frequency (MHz)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=300.0,
                minValue=ITM_MIN_FREQUENCY_MHZ,
                maxValue=ITM_MAX_FREQUENCY_MHZ,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.POLARIZATION,
                "Polarization",
                options=["Horizontal", "Vertical"],
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CLIMATE,
                "Climate zone",
                options=[
                    "Equatorial",
                    "Continental Subtropical",
                    "Maritime Subtropical",
                    "Desert",
                    "Continental Temperate",
                    "Maritime Temperate (land)",
                    "Maritime Temperate (sea)",
                ],
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TIME_PCT,
                "Time percentage",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=50.0,
                minValue=0.01,
                maxValue=99.99,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LOCATION_PCT,
                "Location percentage",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=50.0,
                minValue=0.01,
                maxValue=99.99,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SITUATION_PCT,
                "Situation percentage",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=50.0,
                minValue=0.01,
                maxValue=99.99,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_POWER,
                "TX power (dBm)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=43.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_GAIN,
                "TX antenna gain (dBi)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=8.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_GAIN,
                "RX antenna gain (dBi)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=2.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CABLE_LOSS,
                "Cable loss (dB)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=2.0,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_SENSITIVITY,
                "RX sensitivity (dBm)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=-100.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.K_FACTOR_PRESET,
                "Earth radius factor preset (k)",
                options=[
                    "0.67 - Sub-refractive",
                    "1.00 - Geometric",
                    "1.33 - Standard atmosphere",
                    "2.00 - Super-refractive",
                    "4.00 - Strong super-refractive",
                ],
                defaultValue=2,
            )
        )
        k_factor_param = QgsProcessingParameterNumber(
            self.K_FACTOR,
            "Custom Earth radius factor (k)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=4.0 / 3.0,
            minValue=0.1,
        )
        k_factor_param.setFlags(
            k_factor_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
        )
        self.addParameter(k_factor_param)
        n0_param = QgsProcessingParameterNumber(
            self.N0,
            "Surface refractivity N0 (N-units)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=301.0,
            minValue=ITM_MIN_N0,
            maxValue=ITM_MAX_N0,
        )
        n0_param.setFlags(n0_param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        self.addParameter(n0_param)

        epsilon_param = QgsProcessingParameterNumber(
            self.EPSILON,
            "Earth permittivity (epsilon)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=15.0,
            minValue=1.0,
        )
        epsilon_param.setFlags(
            epsilon_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
        )
        self.addParameter(epsilon_param)

        sigma_param = QgsProcessingParameterNumber(
            self.SIGMA,
            "Earth conductivity (sigma, S/m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.005,
            minValue=ITM_MIN_SIGMA,
        )
        sigma_param.setFlags(
            sigma_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
        )
        self.addParameter(sigma_param)

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_PROFILE, "Profile line output", "GeoPackage files (*.gpkg)"
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_FRESNEL, "Fresnel zone polygon", "GeoPackage files (*.gpkg)"
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_MARKERS, "TX/RX marker output", "GeoPackage files (*.gpkg)"
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_CSV,
                "P2P report CSV",
                "CSV files (*.csv)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_JSON,
                "P2P report JSON",
                "JSON files (*.json)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_HTML,
                "P2P report HTML",
                "HTML files (*.html)",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                "SHOW_CHART",
                "Show profile chart after analysis",
                defaultValue=True,
                optional=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem

        # Parse TX and RX points
        tx_point = self.parameterAsPoint(
            parameters,
            self.TX_POINT,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        rx_point = self.parameterAsPoint(
            parameters,
            self.RX_POINT,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        if tx_point is None or rx_point is None:
            raise ValueError("Both TX and RX points are required.")

        tx_lat = tx_point.y()
        tx_lon = tx_point.x()
        rx_lat = rx_point.y()
        rx_lon = rx_point.x()

        tx_h = self.parameterAsDouble(parameters, self.TX_HEIGHT, context)
        rx_h = self.parameterAsDouble(parameters, self.RX_HEIGHT, context)
        f_mhz = self.parameterAsDouble(parameters, self.FREQ_MHZ, context)
        polarization = self.parameterAsEnum(parameters, self.POLARIZATION, context)
        climate = self.parameterAsEnum(parameters, self.CLIMATE, context)
        time_pct = self.parameterAsDouble(parameters, self.TIME_PCT, context)
        location_pct = self.parameterAsDouble(parameters, self.LOCATION_PCT, context)
        situation_pct = self.parameterAsDouble(parameters, self.SITUATION_PCT, context)
        tx_power = self.parameterAsDouble(parameters, self.TX_POWER, context)
        tx_gain = self.parameterAsDouble(parameters, self.TX_GAIN, context)
        rx_gain = self.parameterAsDouble(parameters, self.RX_GAIN, context)
        cable_loss = self.parameterAsDouble(parameters, self.CABLE_LOSS, context)
        rx_sens = self.parameterAsDouble(parameters, self.RX_SENSITIVITY, context)
        has_preset = self.K_FACTOR_PRESET in parameters
        has_custom = self.K_FACTOR in parameters
        if not has_preset and has_custom:
            k_factor = resolve_k_factor(
                has_preset=False,
                has_custom=True,
                custom_value=self.parameterAsDouble(
                    parameters, self.K_FACTOR, context
                ),
                preset_index=0,
            )
        else:
            k_factor = resolve_k_factor(
                has_preset=has_preset,
                has_custom=has_custom,
                custom_value=0.0,
                preset_index=self.parameterAsEnum(
                    parameters, self.K_FACTOR_PRESET, context
                ),
            )
        n0 = self.parameterAsDouble(parameters, self.N0, context)
        epsilon = self.parameterAsDouble(parameters, self.EPSILON, context)
        sigma = self.parameterAsDouble(parameters, self.SIGMA, context)
        validate_itm_input_ranges(
            tx_height_m=tx_h,
            rx_height_m=rx_h,
            frequency_mhz=f_mhz,
            surface_refractivity_n0=n0,
            earth_conductivity_sigma=sigma,
        )

        dist_m = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)

        feedback.pushInfo(
            "TX: ({:.5f}, {:.5f}), RX: ({:.5f}, {:.5f})".format(
                tx_lat, tx_lon, rx_lat, rx_lon
            )
        )
        feedback.pushInfo(
            "Path distance: {:.1f} m ({:.2f} km)".format(dist_m, dist_m / 1000.0)
        )

        # Download DEM for the path with padding
        pad = max(0.05, dist_m / 111320.0 * 0.1)
        south = min(tx_lat, rx_lat) - pad
        north = max(tx_lat, rx_lat) + pad
        west = min(tx_lon, rx_lon) - pad
        east = max(tx_lon, rx_lon) + pad

        feedback.pushInfo("Downloading DEM data for path...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise RuntimeError("Failed to obtain DEM data for the path area.")

        feedback.setProgress(30)
        feedback.pushInfo("Building elevation grid...")
        elev = ElevationGrid(dem_path)

        # Generate terrain profile
        feedback.pushInfo("Generating terrain profile...")
        points = elev.terrain_profile(tx_lat, tx_lon, rx_lat, rx_lon, step_m=30.0)

        if len(points) < 2:
            raise RuntimeError("Terrain profile too short.")

        distances = [p[0] for p in points]
        elevations = [p[1] for p in points]

        # Fix any NaN elevations
        elevations = [0.0 if math.isnan(e) else e for e in elevations]

        step_m_val = dist_m / max(len(distances) - 1, 1)
        pfl = build_pfl(elevations, step_m_val)

        # ITM prediction
        feedback.pushInfo("Running ITM prediction...")
        feedback.setProgress(50)
        result = itm_p2p_loss(
            h_tx__meter=tx_h,
            h_rx__meter=rx_h,
            profile=pfl,
            climate=climate,
            N0=n0,
            f__mhz=f_mhz,
            polarization=polarization,
            epsilon=epsilon,
            sigma=sigma,
            time_pct=time_pct,
            location_pct=location_pct,
            situation_pct=situation_pct,
        )

        # Fresnel analysis
        tx_elev = elevations[0]
        rx_elev = elevations[-1]
        tx_antenna_h = tx_elev + tx_h
        rx_antenna_h = rx_elev + rx_h
        wavelength_m = 299792458.0 / (f_mhz * 1e6)

        dist_arr = np.asarray(distances, dtype=np.float64)
        elev_arr = np.asarray(elevations, dtype=np.float64)

        terrain_bulge, los_h, fresnel_r, obstructs, vf1, vf60 = (
            fresnel_profile_analysis(
                dist_arr,
                elev_arr,
                tx_antenna_h,
                rx_antenna_h,
                dist_m,
                wavelength_m,
                k_factor,
            )
        )

        los_blocked = bool(obstructs.any())
        f1_violated = bool(vf1.any())
        f60_violated = bool(vf60.any())

        # Link budget
        eirp_dbm = tx_power + tx_gain - cable_loss
        prx_dbm = eirp_dbm + rx_gain - result.loss_db
        margin_db = prx_dbm - rx_sens
        fspl_db = (
            20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(f_mhz) + 32.44
            if dist_m > 0 and f_mhz > 0
            else 0.0
        )

        feedback.setProgress(70)

        # --- Create output layers ---
        temp_dir = tempfile.mkdtemp(prefix="nowires_p2p_")
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        # Use output parameter destinations if provided, else temp dir
        profile_dest = self.parameterAsFileOutput(
            parameters, self.OUTPUT_PROFILE, context
        )
        fresnel_dest = self.parameterAsFileOutput(
            parameters, self.OUTPUT_FRESNEL, context
        )

        # 1. Profile line layer
        profile_path = (
            profile_dest if profile_dest else os.path.join(temp_dir, "profile_line.shp")
        )
        self._write_profile_line(
            profile_path, srs, tx_lat, tx_lon, rx_lat, rx_lon, dist_m, result
        )

        # 2. Fresnel zone polygon + terrain/LOS lines layers (separate files)
        fresnel_poly_path = (
            fresnel_dest if fresnel_dest else os.path.join(temp_dir, "fresnel_zone.shp")
        )
        markers_dest = self.parameterAsFileOutput(
            parameters, self.OUTPUT_MARKERS, context
        )
        markers_path = (
            markers_dest if markers_dest else os.path.join(temp_dir, "p2p_markers.shp")
        )
        # Derive the lines path from the polygon path. Use os.path.splitext
        # so it works for any extension (.shp, .gpkg, .geojson, ...) — the
        # old ".shp" string replace was a silent no-op for non-shapefile
        # destinations and led to both layers writing to the same file.
        _poly_root, _poly_ext = os.path.splitext(fresnel_poly_path)
        fresnel_lines_path = "{}_lines{}".format(_poly_root, _poly_ext)

        self._write_fresnel_zone(
            fresnel_poly_path,
            fresnel_lines_path,
            srs,
            tx_lat,
            tx_lon,
            rx_lat,
            rx_lon,
            dist_arr,
            terrain_bulge,
            los_h,
            fresnel_r,
            dist_m,
        )
        write_p2p_marker_layer(
            markers_path,
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            rx_lat=rx_lat,
            rx_lon=rx_lon,
            tx_h=tx_h,
            rx_h=rx_h,
            tx_gain=tx_gain,
            rx_gain=rx_gain,
            tx_power_dbm=tx_power,
            rx_sensitivity_dbm=rx_sens,
        )

        report_payload = build_p2p_report_payload(
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            rx_lat=rx_lat,
            rx_lon=rx_lon,
            tx_h=tx_h,
            rx_h=rx_h,
            f_mhz=f_mhz,
            polarization_name=POLARIZATION_NAMES.get(polarization, str(polarization)),
            climate_name=CLIMATE_NAMES.get(climate, str(climate)),
            k_factor=k_factor,
            dist_m=dist_m,
            propagation_mode=result.mode,
            propagation_mode_name=PROP_MODE_NAMES.get(result.mode, "Unknown"),
            fspl_db=fspl_db,
            itm_loss_db=result.loss_db,
            tx_power=tx_power,
            tx_gain=tx_gain,
            rx_gain=rx_gain,
            cable_loss=cable_loss,
            eirp_dbm=eirp_dbm,
            prx_dbm=prx_dbm,
            rx_sensitivity_dbm=rx_sens,
            margin_db=margin_db,
            los_blocked=los_blocked,
            fresnel_1_violated=f1_violated,
            fresnel_60_violated=f60_violated,
            max_fresnel_radius_m=float(fresnel_r.max()),
        )
        report_csv_path = self.parameterAsFileOutput(
            parameters, self.OUTPUT_REPORT_CSV, context
        )
        report_json_path = self.parameterAsFileOutput(
            parameters, self.OUTPUT_REPORT_JSON, context
        )
        report_html_path = self.parameterAsFileOutput(
            parameters, self.OUTPUT_REPORT_HTML, context
        )
        if report_csv_path:
            write_report_csv(report_csv_path, report_payload)
        if report_json_path:
            write_report_json(report_json_path, report_payload)
        if report_html_path:
            write_report_html(report_html_path, report_payload, title="NoWires P2P Report")

        feedback.setProgress(90)

        # Load layers
        profile_layer = QgsVectorLayer(
            profile_path,
            "P2P Link ({:.0f} MHz, {:.1f} km)".format(f_mhz, dist_m / 1000),
        )
        fresnel_poly_layer = QgsVectorLayer(
            fresnel_poly_path, "Fresnel Zone Analysis"
        )
        fresnel_lines_layer = QgsVectorLayer(
            fresnel_lines_path, "Fresnel Zone Lines"
        )
        marker_layer = QgsVectorLayer(markers_path, "P2P TX/RX Markers")

        _queue_layer_for_loading(context, fresnel_poly_layer, "Fresnel Zone Analysis")
        _queue_layer_for_loading(context, fresnel_lines_layer, "Fresnel Zone Lines")
        _queue_layer_for_loading(
            context,
            profile_layer,
            "P2P Link ({:.0f} MHz, {:.1f} km)".format(f_mhz, dist_m / 1000),
        )
        _queue_layer_for_loading(context, marker_layer, "P2P TX/RX Markers")

        # Show profile chart if requested
        show_chart = self.parameterAsBool(parameters, self.SHOW_CHART, context)
        if show_chart:
            self._show_profile_chart(
                dist_arr,
                elev_arr,
                terrain_bulge,
                los_h,
                fresnel_r,
                dist_m,
                tx_h,
                rx_h,
                f_mhz,
                result,
                k_factor,
                tx_power,
                tx_gain,
                rx_gain,
                cable_loss,
                rx_sens,
            )

        feedback.setProgress(100)

        # Report
        feedback.pushInfo("")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo("P2P ANALYSIS RESULTS")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo(
            "Distance: {:.1f} m ({:.2f} km)".format(dist_m, dist_m / 1000)
        )
        feedback.pushInfo("Frequency: {:.1f} MHz".format(f_mhz))
        feedback.pushInfo(
            "Propagation mode: {} ({})".format(
                result.mode, PROP_MODE_NAMES.get(result.mode, "Unknown")
            )
        )
        feedback.pushInfo("")
        feedback.pushInfo("LINK BUDGET")
        feedback.pushInfo("  TX Power:       {:.2f} dBm".format(tx_power))
        feedback.pushInfo("  TX Gain:        {:.2f} dBi".format(tx_gain))
        feedback.pushInfo("  Cable Loss:     {:.2f} dB".format(cable_loss))
        feedback.pushInfo("  EIRP:           {:.2f} dBm".format(eirp_dbm))
        feedback.pushInfo("  Free Space Loss:{:.2f} dB".format(fspl_db))
        feedback.pushInfo("  ITM Path Loss:  {:.2f} dB".format(result.loss_db))
        feedback.pushInfo(
            "  Excess Loss:    {:.2f} dB".format(result.loss_db - fspl_db)
        )
        feedback.pushInfo("  RX Gain:        {:.2f} dBi".format(rx_gain))
        feedback.pushInfo("  Received Power: {:.2f} dBm".format(prx_dbm))
        feedback.pushInfo("  RX Sensitivity: {:.2f} dBm".format(rx_sens))
        feedback.pushInfo("  Link Margin:    {:.2f} dB".format(margin_db))
        feedback.pushInfo(
            "  Fade Margin Class: {}".format(
                report_payload["results"]["fade_margin_class"]
            )
        )
        feedback.pushInfo(
            "  Reliability:     {}".format(
                report_payload["results"]["reliability_summary"]
            )
        )
        feedback.pushInfo(
            "  Availability Method: {}".format(
                report_payload["results"]["availability_method"]
            )
        )
        if report_payload["results"]["availability_estimate_pct"] is not None:
            feedback.pushInfo(
                "  Availability Estimate: {:.2f}%".format(
                    report_payload["results"]["availability_estimate_pct"]
                )
            )
        feedback.pushInfo("")
        feedback.pushInfo("FRESNEL ZONE ANALYSIS (k={:.3f})".format(k_factor))
        feedback.pushInfo(
            "  LOS Blocked:         {}".format("YES" if los_blocked else "NO")
        )
        feedback.pushInfo(
            "  1st Fresnel violated: {}".format("YES" if f1_violated else "NO")
        )
        feedback.pushInfo(
            "  60% Fresnel rule violated: {}".format("YES" if f60_violated else "NO")
        )
        feedback.pushInfo(
            "  Max 1st Fresnel radius: {:.1f} m".format(float(fresnel_r.max()))
        )
        feedback.pushInfo("")
        if margin_db >= 0:
            feedback.pushInfo(
                "LINK STATUS: VIABLE (margin {:.1f} dB above sensitivity)".format(
                    margin_db
                )
            )
        else:
            feedback.pushInfo(
                "LINK STATUS: NOT VIABLE (margin {:.1f} dB below sensitivity)".format(
                    margin_db
                )
            )
        feedback.pushInfo("=" * 50)

        return {
            self.OUTPUT_PROFILE: profile_path,
            self.OUTPUT_FRESNEL: fresnel_poly_path,
            self.OUTPUT_MARKERS: markers_path,
            self.OUTPUT_REPORT_CSV: report_csv_path,
            self.OUTPUT_REPORT_JSON: report_json_path,
            self.OUTPUT_REPORT_HTML: report_html_path,
        }

    def _write_profile_line(
        self, path, srs, tx_lat, tx_lon, rx_lat, rx_lon, dist_m, result
    ):
        """Write the P2P link line, picking the OGR driver from the path extension."""

        driver = ogr.GetDriverByName(ogr_driver_for_path(path))
        _remove_existing_ogr_dataset(driver, path)
        ds = driver.CreateDataSource(path)
        layer = ds.CreateLayer("link", srs=srs, geom_type=ogr.wkbLineString)
        layer.CreateField(ogr.FieldDefn("distance", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("loss_db", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("mode", ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn("mode_name", ogr.OFTString))

        feat = ogr.Feature(layer.GetLayerDefn())
        geom = ogr.Geometry(ogr.wkbLineString)
        geom.AddPoint(tx_lon, tx_lat)
        geom.AddPoint(rx_lon, rx_lat)
        feat.SetGeometry(geom)
        feat.SetField("distance", dist_m)
        feat.SetField("loss_db", result.loss_db)
        feat.SetField("mode", result.mode)
        feat.SetField("mode_name", PROP_MODE_NAMES.get(result.mode, "Unknown"))
        layer.CreateFeature(feat)
        ds = None

    def _write_fresnel_zone(
        self,
        poly_path,
        lines_path,
        srs,
        tx_lat,
        tx_lon,
        rx_lat,
        rx_lon,
        distances,
        terrain_bulge,
        los_h,
        fresnel_r,
        dist_m,
    ):
        """Write Fresnel zone polygons and profile lines to separate shapefiles.

        ESRI Shapefile enforces a single geometry type per file, so polygons
        and lines must be split across two files:

        * *poly_path* — Fresnel zone polygons (wkbPolygon).
        * *lines_path* — Terrain profile and LOS lines (wkbLineString).

        All features use geographic (lon, lat) coordinates; height is stored as Z.
        The OGR driver for each file is selected from its extension so that
        Processing destinations like ``.gpkg`` or ``.geojson`` work too.
        Returns (poly_path, lines_path).
        """
        poly_driver = ogr.GetDriverByName(ogr_driver_for_path(poly_path))
        lines_driver = ogr.GetDriverByName(ogr_driver_for_path(lines_path))
        _remove_existing_ogr_dataset(poly_driver, poly_path)
        _remove_existing_ogr_dataset(lines_driver, lines_path)
        n = len(distances)

        def _geo_points(heights):
            """Convert path-locals heights to (lon, lat, z) geographic points."""
            pts = []
            for i in range(n):
                t = distances[i] / dist_m if dist_m > 0 else 0
                lat = tx_lat + t * (rx_lat - tx_lat)
                lon = tx_lon + t * (rx_lon - tx_lon)
                pts.append((float(lon), float(lat), float(heights[i])))
            return pts

        # ---- Polygon layer (Fresnel zones) ----
        ds_poly = poly_driver.CreateDataSource(poly_path)
        layer_poly = ds_poly.CreateLayer(
            "fresnel_zones", srs=srs, geom_type=ogr.wkbPolygon
        )
        layer_poly.CreateField(ogr.FieldDefn("type", ogr.OFTString))
        layer_poly.CreateField(ogr.FieldDefn("blocked", ogr.OFTInteger))

        # 1st Fresnel zone polygon
        upper_pts = _geo_points(los_h + fresnel_r)
        lower_pts = _geo_points(los_h - fresnel_r)

        ring_f1 = ogr.Geometry(ogr.wkbLinearRing)
        for lon, lat, z in upper_pts:
            ring_f1.AddPoint(lon, lat, z)
        for lon, lat, z in reversed(lower_pts):
            ring_f1.AddPoint(lon, lat, z)
        ring_f1.AddPoint(upper_pts[0][0], upper_pts[0][1], upper_pts[0][2])

        poly_f1 = ogr.Geometry(ogr.wkbPolygon)
        poly_f1.AddGeometry(ring_f1)

        feat_f1 = ogr.Feature(layer_poly.GetLayerDefn())
        feat_f1.SetGeometry(poly_f1)
        feat_f1.SetField("type", "fresnel_zone")
        feat_f1.SetField("blocked", 0)
        layer_poly.CreateFeature(feat_f1)

        # Fresnel violation band: the slice between the 1st-Fresnel lower
        # boundary (los_h - r) and the 60% lower boundary (los_h - 0.6r).
        # Terrain entering this band already eats more than 40% of the
        # first Fresnel zone, which is the conventional engineering limit.
        # This is NOT a symmetric ±0.6r zone around the LOS.
        upper_band = _geo_points(los_h - 0.6 * fresnel_r)
        lower_band = _geo_points(los_h - fresnel_r)

        ring_band = ogr.Geometry(ogr.wkbLinearRing)
        for lon, lat, z in upper_band:
            ring_band.AddPoint(lon, lat, z)
        for lon, lat, z in reversed(lower_band):
            ring_band.AddPoint(lon, lat, z)
        ring_band.AddPoint(upper_band[0][0], upper_band[0][1], upper_band[0][2])

        poly_band = ogr.Geometry(ogr.wkbPolygon)
        poly_band.AddGeometry(ring_band)

        feat_band = ogr.Feature(layer_poly.GetLayerDefn())
        feat_band.SetGeometry(poly_band)
        feat_band.SetField("type", "fresnel_violation_band_60pct")
        feat_band.SetField("blocked", 0)
        layer_poly.CreateFeature(feat_band)

        ds_poly = None

        # ---- Line layer (terrain + LOS) ----
        ds_lines = lines_driver.CreateDataSource(lines_path)
        layer_lines = ds_lines.CreateLayer(
            "fresnel_lines", srs=srs, geom_type=ogr.wkbLineString
        )
        layer_lines.CreateField(ogr.FieldDefn("type", ogr.OFTString))
        layer_lines.CreateField(ogr.FieldDefn("blocked", ogr.OFTInteger))

        # Terrain profile line
        terrain_pts = _geo_points(terrain_bulge)
        terrain_line = ogr.Geometry(ogr.wkbLineString)
        for lon, lat, z in terrain_pts:
            terrain_line.AddPoint(lon, lat, z)

        feat_ter = ogr.Feature(layer_lines.GetLayerDefn())
        feat_ter.SetGeometry(terrain_line)
        feat_ter.SetField("type", "terrain")
        feat_ter.SetField("blocked", int(bool((terrain_bulge > los_h).any())))
        layer_lines.CreateFeature(feat_ter)

        # LOS line
        los_pts = _geo_points(los_h)
        los_line = ogr.Geometry(ogr.wkbLineString)
        for lon, lat, z in los_pts:
            los_line.AddPoint(lon, lat, z)

        feat_los = ogr.Feature(layer_lines.GetLayerDefn())
        feat_los.SetGeometry(los_line)
        feat_los.SetField("type", "los")
        feat_los.SetField("blocked", 0)
        layer_lines.CreateFeature(feat_los)

        ds_lines = None
        return poly_path, lines_path

    def _show_profile_chart(
        self,
        distances,
        elevations,
        terrain_bulge,
        los_h,
        fresnel_r,
        dist_m,
        tx_h,
        rx_h,
        f_mhz,
        result,
        k_factor,
        tx_power,
        tx_gain,
        rx_gain,
        cable_loss,
        rx_sens,
    ):
        """Show a matplotlib profile chart as a non-modal dialog."""
        try:
            import matplotlib
            backend_name, _backend_module = matplotlib_qt_backend()
            matplotlib.use(backend_name)
            import matplotlib.pyplot as plt
            from qgis.PyQt.QtWidgets import QDockWidget
            from qgis.PyQt.QtCore import Qt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        except ImportError:
            logger.warning("matplotlib not available, skipping profile chart")
            return

        d_km = np.asarray(distances, dtype=np.float64) / 1000.0

        fig, ax = plt.subplots(figsize=(10, 5))

        # Terrain + earth bulge
        ax.fill_between(
            d_km, np.min(terrain_bulge) - 10, terrain_bulge,
            color="#8B6914", alpha=0.5, label="Terrain",
        )
        ax.plot(d_km, terrain_bulge, color="#8B6914", linewidth=1.0)

        # LOS
        ax.plot(d_km, los_h, "g--", linewidth=1.2, label="Line of Sight")

        # 1st Fresnel zone (upper and lower boundaries)
        f1_upper = los_h + fresnel_r
        f1_lower = los_h - fresnel_r
        ax.fill_between(
            d_km, f1_lower, f1_upper,
            color="cyan", alpha=0.15, label="1st Fresnel Zone",
        )
        ax.plot(d_km, f1_upper, "c:", linewidth=0.8)
        ax.plot(d_km, f1_lower, "c:", linewidth=0.8)

        # Fresnel violation band: terrain reaching into this slice already
        # blocks >40% of the 1st Fresnel zone (the engineering limit).
        f60_upper = los_h - 0.6 * fresnel_r
        ax.fill_between(
            d_km, f1_lower, f60_upper,
            color="blue", alpha=0.12, label="Fresnel Violation Band (>40%)",
        )

        # TX and RX antenna markers
        ax.plot(0, los_h[0], "r^", markersize=12, label="TX", zorder=5)
        ax.plot(d_km[-1], los_h[-1], "rv", markersize=12, label="RX", zorder=5)

        # Labels and styling
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Height (m)")
        ax.set_title(
            "P2P Profile: {:.1f} MHz, {:.2f} km (k={:.3f})".format(
                f_mhz, dist_m / 1000, k_factor
            )
        )
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

        # Add link budget text box
        eirp = tx_power + tx_gain - cable_loss
        prx = eirp + rx_gain - result.loss_db
        margin = prx - rx_sens
        status = "VIABLE" if margin >= 0 else "NOT VIABLE"
        textstr = (
            "Loss: {:.1f} dB\n"
            "Prx: {:.1f} dBm\n"
            "Margin: {:.1f} dB\n"
            "Status: {}".format(result.loss_db, prx, margin, status)
        )
        props = dict(boxstyle="round", facecolor="wheat", alpha=0.8)
        ax.text(
            0.02, 0.98, textstr,
            transform=ax.transAxes, fontsize=9,
            verticalalignment="top", bbox=props,
        )

        fig.tight_layout()

        # Embed in a QGIS dock widget so it doesn't block the UI
        canvas = FigureCanvasQTAgg(fig)
        from qgis.utils import iface as qgis_iface
        dock = QDockWidget("P2P Profile Chart", qgis_iface.mainWindow())
        dock.setWidget(canvas)
        dock.setFloating(True)
        dock.setAttribute(widget_attribute_delete_on_close(Qt))
        qgis_iface.addDockWidget(dock_widget_area_right(Qt), dock)

    def name(self):
        return "p2p_analysis"

    def displayName(self):
        return self.tr("Point-to-Point Analysis")

    def group(self):
        return self.tr("Radio Propagation")

    def groupId(self):
        return "radio_propagation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return P2PAlgorithm()
