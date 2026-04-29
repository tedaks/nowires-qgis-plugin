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


Batch P2P Analysis Algorithm.

Supports two modes:
- One-to-Many: single TX point to multiple RX points from a vector layer
- Many-to-One: multiple candidate TX sites from a vector layer to single RX point

Results are ranked by link margin and exported with a marker layer.

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
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
)
try:
    from qgis.core import NULL as _QGIS_NULL
except ImportError:
    _QGIS_NULL = None
from osgeo import ogr, osr

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid, bearing_deg, haversine_m
from .radio import (
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MIN_TERMINAL_HEIGHT_M,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_N0,
    ITM_MAX_N0,
    ITM_MIN_SIGMA,
    K_FACTOR_PRESETS,
    build_pfl,
    itm_p2p_loss,
    resolve_k_factor,
    validate_itm_input_ranges,
)
from .antenna import (
    ANTENNA_PRESET_OPTIONS,
    ANTENNA_PRESET_KEYS,
    antenna_config_from_values,
    antenna_gain_adjustment_db,
)
from .clutter import (
    CLUTTER_MODEL_OPTIONS,
    CLUTTER_OVERRIDE_OPTIONS,
    LandCoverGrid,
    clutter_override_value,
    compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area,
)
from .processing_utils import queue_layer_for_loading
from .report_payloads import ogr_driver_for_path, _remove_existing_ogr_dataset

BATCH_MODE_OPTIONS = ["One-to-Many (single TX → multiple RX)", "Many-to-One (multiple TX → single RX)"]
RANK_BY_OPTIONS = ["Link margin (descending)", "Path loss (ascending)", "Clearance (descending)"]


def _feat_attr(feat, name, default):
    """Return feat.attribute(name) cast to the same type as default.

    If default is None, returns float for numeric values or str for strings.
    Returns default on NULL attribute, missing field, or cast failure.
    """
    val = feat.attribute(name)
    if val is None or val == _QGIS_NULL:
        return default
    if default is None:
        if isinstance(val, (int, float)):
            return float(val)
        return str(val) if isinstance(val, str) else default
    try:
        if isinstance(default, float):
            return float(val)
        if isinstance(default, int):
            return int(float(val))
        if isinstance(default, str):
            return str(val)
        return default
    except (ValueError, TypeError):
        return default



class BatchAnalysisAlgorithm(QgsProcessingAlgorithm):
    """Batch point-to-point link analysis."""

    MODE = "MODE"
    TX_POINT = "TX_POINT"
    RX_LAYER = "RX_LAYER"
    RX_POINT = "RX_POINT"
    TX_LAYER = "TX_LAYER"
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
    TX_ANTENNA_PRESET = "TX_ANTENNA_PRESET"
    TX_ANTENNA_AZ = "TX_ANTENNA_AZ"
    TX_FRONT_BACK_DB = "TX_FRONT_BACK_DB"
    RX_ANTENNA_PRESET = "RX_ANTENNA_PRESET"
    RX_ANTENNA_AZ = "RX_ANTENNA_AZ"
    RX_FRONT_BACK_DB = "RX_FRONT_BACK_DB"
    CLUTTER_MODEL = "CLUTTER_MODEL"
    CLUTTER_RASTER = "CLUTTER_RASTER"
    TX_CLUTTER_OVERRIDE = "TX_CLUTTER_OVERRIDE"
    RX_CLUTTER_OVERRIDE = "RX_CLUTTER_OVERRIDE"
    K_FACTOR_PRESET = "K_FACTOR_PRESET"
    K_FACTOR = "K_FACTOR"
    N0 = "N0"
    EPSILON = "EPSILON"
    SIGMA = "SIGMA"
    RANK_BY = "RANK_BY"
    OUTPUT_MARKERS = "OUTPUT_MARKERS"
    OUTPUT_CSV = "OUTPUT_CSV"
    OUTPUT_JSON = "OUTPUT_JSON"

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterEnum(
                self.MODE, "Analysis mode", options=BATCH_MODE_OPTIONS, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterPoint(
                self.TX_POINT, "TX point (for One-to-Many)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.RX_LAYER,
                "RX point layer (for One-to-Many)",
                [QgsProcessingParameterFeatureSource.GeometryType.Point],
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterPoint(
                self.RX_POINT, "RX point (for Many-to-One)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TX_LAYER,
                "TX candidate layer (for Many-to-One)",
                [QgsProcessingParameterFeatureSource.GeometryType.Point],
                optional=True,
            )
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
                self.TX_POWER, "TX power (dBm)",
                type=QgsProcessingParameterNumber.Double, defaultValue=43.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_GAIN, "TX antenna gain (dBi)",
                type=QgsProcessingParameterNumber.Double, defaultValue=8.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_GAIN, "RX antenna gain (dBi)",
                type=QgsProcessingParameterNumber.Double, defaultValue=2.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CABLE_LOSS, "Cable loss (dB)",
                type=QgsProcessingParameterNumber.Double, defaultValue=2.0, minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_SENSITIVITY, "RX sensitivity (dBm)",
                type=QgsProcessingParameterNumber.Double, defaultValue=-100.0,
            )
        )
        self.addParameter(QgsProcessingParameterEnum(
            self.TX_ANTENNA_PRESET, "TX antenna preset",
            options=ANTENNA_PRESET_OPTIONS, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.TX_ANTENNA_AZ, "TX antenna azimuth (deg)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.TX_FRONT_BACK_DB, "TX front-to-back ratio (dB)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=25.0, minValue=0.0,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.RX_ANTENNA_PRESET, "RX antenna preset",
            options=ANTENNA_PRESET_OPTIONS, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.RX_ANTENNA_AZ, "RX antenna azimuth (deg)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.RX_FRONT_BACK_DB, "RX front-to-back ratio (dB)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=25.0, minValue=0.0,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.CLUTTER_MODEL, "Clutter correction",
            options=CLUTTER_MODEL_OPTIONS, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterFile(
            self.CLUTTER_RASTER, "Land-cover raster (auto-downloaded if blank)",
            extension="tif", optional=True,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.TX_CLUTTER_OVERRIDE, "TX clutter override",
            options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.RX_CLUTTER_OVERRIDE, "RX clutter override",
            options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0,
        ))
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
                    "Custom",
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
        n0_param.setFlags(
            n0_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
        )
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
            QgsProcessingParameterEnum(
                self.RANK_BY,
                "Rank results by",
                options=RANK_BY_OPTIONS,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_MARKERS,
                "Ranked marker layer output",
                "GeoPackage files (*.gpkg)",
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_CSV,
                "Batch results CSV",
                "CSV files (*.csv)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_JSON,
                "Batch results JSON",
                "JSON files (*.json)",
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem

        mode = self.parameterAsEnum(parameters, self.MODE, context)
        rank_by = self.parameterAsEnum(parameters, self.RANK_BY, context)

        if mode == 0:
            tx_point = self.parameterAsPoint(
                parameters,
                self.TX_POINT,
                context,
                crs=QgsCoordinateReferenceSystem("EPSG:4326"),
            )
            if tx_point is None:
                raise QgsProcessingException("TX point is required for One-to-Many mode.")
            tx_lat = tx_point.y()
            tx_lon = tx_point.x()

            rx_source = self.parameterAsFeatureSource(parameters, self.RX_LAYER, context)
            if rx_source is None:
                raise QgsProcessingException("RX layer is required for One-to-Many mode.")
            rx_features = list(rx_source.getFeatures())
            if not rx_features:
                raise QgsProcessingException("RX layer has no features.")

            rx_points = []
            for feat in rx_features:
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                if geom.isMultipart():
                    continue
                pt = geom.asPoint()
                height = _feat_attr(feat, "height", 10.0)
                preset_key = str(_feat_attr(feat, "antenna_preset", "omni"))
                az = _feat_attr(feat, "azimuth", 0.0)
                gain = _feat_attr(feat, "gain_db", None)
                rx_points.append({
                    "id": feat.id(),
                    "lat": pt.y(),
                    "lon": pt.x(),
                    "height": height,
                    "antenna_preset": preset_key,
                    "azimuth": az,
                    "gain_db": gain,
                })
            if not rx_points:
                raise QgsProcessingException("No valid RX points found.")
            feedback.pushInfo(
                "One-to-Many: {} RX points from layer".format(len(rx_points))
            )

            candidate_tx = [{"lat": tx_lat, "lon": tx_lon, "height": None, "is_tx": True}]

        else:
            tx_source = self.parameterAsFeatureSource(parameters, self.TX_LAYER, context)
            if tx_source is None:
                raise QgsProcessingException("TX layer is required for Many-to-One mode.")
            tx_features = list(tx_source.getFeatures())
            if not tx_features:
                raise QgsProcessingException("TX layer has no features.")

            candidate_tx = []
            for feat in tx_features:
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                if geom.isMultipart():
                    continue
                pt = geom.asPoint()
                height = _feat_attr(feat, "height", 30.0)
                preset_key = str(_feat_attr(feat, "antenna_preset", "omni"))
                az = _feat_attr(feat, "azimuth", 0.0)
                gain = _feat_attr(feat, "gain_db", None)
                candidate_tx.append({
                    "id": feat.id(),
                    "lat": pt.y(),
                    "lon": pt.x(),
                    "height": height,
                    "antenna_preset": preset_key,
                    "azimuth": az,
                    "gain_db": gain,
                    "is_tx": True,
                })
            if not candidate_tx:
                raise QgsProcessingException("No valid TX points found.")

            rx_point = self.parameterAsPoint(
                parameters,
                self.RX_POINT,
                context,
                crs=QgsCoordinateReferenceSystem("EPSG:4326"),
            )
            if rx_point is None:
                raise QgsProcessingException("RX point is required for Many-to-One mode.")
            rx_lat = rx_point.y()
            rx_lon = rx_point.x()
            rx_points = [{"id": 0, "lat": rx_lat, "lon": rx_lon, "height": None, "is_tx": False}]
            feedback.pushInfo(
                "Many-to-One: {} candidate TX sites".format(len(candidate_tx))
            )

        tx_h = self.parameterAsDouble(parameters, self.TX_HEIGHT, context)
        rx_h = self.parameterAsDouble(parameters, self.RX_HEIGHT, context)
        f_mhz = self.parameterAsDouble(parameters, self.FREQ_MHZ, context)
        polarization = self.parameterAsEnum(parameters, self.POLARIZATION, context)
        climate = self.parameterAsEnum(parameters, self.CLIMATE, context)
        time_pct = self.parameterAsDouble(parameters, self.TIME_PCT, context)
        location_pct = self.parameterAsDouble(parameters, self.LOCATION_PCT, context)
        situation_pct = self.parameterAsDouble(parameters, self.SITUATION_PCT, context)
        tx_power = self.parameterAsDouble(parameters, self.TX_POWER, context)
        tx_gain_default = self.parameterAsDouble(parameters, self.TX_GAIN, context)
        rx_gain_default = self.parameterAsDouble(parameters, self.RX_GAIN, context)
        cable_loss = self.parameterAsDouble(parameters, self.CABLE_LOSS, context)
        rx_sens = self.parameterAsDouble(parameters, self.RX_SENSITIVITY, context)
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

        validate_itm_input_ranges(
            tx_height_m=tx_h,
            rx_height_m=rx_h,
            frequency_mhz=f_mhz,
            surface_refractivity_n0=n0,
            earth_conductivity_sigma=sigma,
        )
        clutter_enabled = self.parameterAsEnum(parameters, self.CLUTTER_MODEL, context) == 1
        clutter_raster_path = self.parameterAsFile(parameters, self.CLUTTER_RASTER, context)
        if clutter_raster_path:
            clutter_grid = LandCoverGrid.from_raster(clutter_raster_path)
        else:
            clutter_grid = None
        tx_clutter_override = clutter_override_value(
            self.parameterAsEnum(parameters, self.TX_CLUTTER_OVERRIDE, context)
        )
        rx_clutter_override = clutter_override_value(
            self.parameterAsEnum(parameters, self.RX_CLUTTER_OVERRIDE, context)
        )

        all_lats = [p["lat"] for p in candidate_tx] + [p["lat"] for p in rx_points]
        all_lons = [p["lon"] for p in candidate_tx] + [p["lon"] for p in rx_points]
        south = min(all_lats)
        north = max(all_lats)
        west = min(all_lons)
        east = max(all_lons)
        pad = max(0.05, (north - south) * 0.1)

        if clutter_grid is None and clutter_enabled:
            clutter_grid = ensure_clutter_grid_for_area(
                south=south - pad,
                north=north + pad,
                west=west - pad,
                east=east + pad,
                feedback=feedback,
            )

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(
            south - pad, north + pad, west - pad, east + pad, feedback=feedback
        )
        if dem_path is None:
            raise QgsProcessingException("Failed to obtain DEM data for the analysis area.")
        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(15)
        elev = ElevationGrid(dem_path)

        feedback.pushInfo("Computing batch P2P links...")
        feedback.setProgress(20)

        results = []
        total = len(candidate_tx) * len(rx_points)
        count = 0
        wavelength_m = 299792458.0 / (f_mhz * 1e6)
        tx_front_back_db = self.parameterAsDouble(parameters, self.TX_FRONT_BACK_DB, context)
        rx_front_back_db = self.parameterAsDouble(parameters, self.RX_FRONT_BACK_DB, context)

        for tx_def in candidate_tx:
            tx_lat = tx_def["lat"]
            tx_lon = tx_def["lon"]
            tx_h_eff = tx_def["height"] if tx_def["height"] is not None else tx_h

            for rx_def in rx_points:
                if feedback.isCanceled():
                    raise QgsProcessingException("Batch analysis cancelled by user.")
                rx_lat = rx_def["lat"]
                rx_lon = rx_def["lon"]
                rx_h_eff = rx_def["height"] if rx_def["height"] is not None else rx_h

                try:
                    dist_m = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)
                    if dist_m < 1.0:
                        count += 1
                        continue

                    profile_points = elev.terrain_profile(tx_lat, tx_lon, rx_lat, rx_lon, step_m=30.0)
                    if len(profile_points) < 2:
                        count += 1
                        continue
                    distances = [p[0] for p in profile_points]
                    elevations = [p[1] for p in profile_points]
                    elevations = [0.0 if math.isnan(e) else e for e in elevations]
                    step_m_val = dist_m / max(len(distances) - 1, 1)
                    pfl = build_pfl(elevations, step_m_val)

                    itm_result = itm_p2p_loss(
                        h_tx__meter=tx_h_eff,
                        h_rx__meter=rx_h_eff,
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

                    clutter_losses = compute_terminal_clutter_losses(
                        tx_lat=tx_lat,
                        tx_lon=tx_lon,
                        rx_lat=rx_lat,
                        rx_lon=rx_lon,
                        frequency_mhz=f_mhz,
                        enabled=clutter_enabled,
                        land_cover_grid=clutter_grid,
                        tx_override=tx_clutter_override,
                        rx_override=rx_clutter_override,
                    )

                    total_loss_db = itm_result.loss_db + clutter_losses.total_loss_db

                    tx_bearing = bearing_deg(tx_lat, tx_lon, rx_lat, rx_lon)
                    rx_bearing = bearing_deg(rx_lat, rx_lon, tx_lat, tx_lon)
                    vertical_angle = math.degrees(
                        math.atan2((elevations[-1] + rx_h_eff) - (elevations[0] + tx_h_eff), max(dist_m, 1.0))
                    )

                    tx_gain_eff = tx_def["gain_db"] if tx_def["gain_db"] is not None else tx_gain_default
                    rx_gain_eff = rx_def["gain_db"] if rx_def["gain_db"] is not None else rx_gain_default

                    tx_preset_key = tx_def.get("antenna_preset", "omni")
                    if tx_preset_key not in ANTENNA_PRESET_KEYS:
                        tx_preset_key = "omni"
                    tx_preset_idx = ANTENNA_PRESET_KEYS.index(tx_preset_key)
                    tx_ant_config = antenna_config_from_values(
                        preset=tx_preset_idx,
                        azimuth_deg=tx_def.get("azimuth", 0.0),
                        front_back_db=tx_front_back_db,
                    )
                    rx_preset_key = rx_def.get("antenna_preset", "omni")
                    if rx_preset_key not in ANTENNA_PRESET_KEYS:
                        rx_preset_key = "omni"
                    rx_preset_idx = ANTENNA_PRESET_KEYS.index(rx_preset_key)
                    rx_ant_config = antenna_config_from_values(
                        preset=rx_preset_idx,
                        azimuth_deg=rx_def.get("azimuth", 0.0),
                        front_back_db=rx_front_back_db,
                    )

                    tx_ant_adj = antenna_gain_adjustment_db(tx_bearing, vertical_angle, tx_ant_config)
                    rx_ant_adj = antenna_gain_adjustment_db(rx_bearing, -vertical_angle, rx_ant_config)
                    ant_gain_adj_total = tx_ant_adj + rx_ant_adj

                    eirp_eff = tx_power + tx_gain_eff - cable_loss
                    prx_dbm = eirp_eff + rx_gain_eff + ant_gain_adj_total - total_loss_db
                    margin_db = prx_dbm - rx_sens

                    fresnel_r_arr = []
                    for i in range(len(distances)):
                        d1 = distances[i]
                        d2 = dist_m - d1
                        if d1 > 0 and d2 > 0:
                            fr = math.sqrt(wavelength_m * d1 * d2 / dist_m)
                            fresnel_r_arr.append(fr)
                        else:
                            fresnel_r_arr.append(0.0)

                    fresnel_r_arr = np.array(fresnel_r_arr, dtype=np.float64)
                    elev_arr = np.array(elevations, dtype=np.float64)
                    dist_arr = np.array(distances, dtype=np.float64)

                    tx_antenna_h = elevations[0] + tx_h_eff
                    rx_antenna_h = elevations[-1] + rx_h_eff
                    t = np.divide(dist_arr, dist_m, out=np.zeros_like(dist_arr), where=dist_m > 0)
                    a_eff = k_factor * 6371000.0
                    bulge = (dist_arr * (dist_m - dist_arr)) / (2.0 * a_eff)
                    los_h = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)
                    terrain_bulge = elev_arr + bulge
                    fresnel_clearance = (los_h - fresnel_r_arr) - terrain_bulge
                    clearance_pct = float(
                        np.sum(fresnel_clearance > 0) / max(len(fresnel_clearance), 1) * 100
                    )

                    results.append({
                        "tx_lat": tx_lat,
                        "tx_lon": tx_lon,
                        "rx_lat": rx_lat,
                        "rx_lon": rx_lon,
                        "dist_m": dist_m,
                        "dist_km": dist_m / 1000.0,
                        "itm_loss_db": itm_result.loss_db,
                        "total_loss_db": total_loss_db,
                        "prx_dbm": prx_dbm,
                        "margin_db": margin_db,
                        "clearance_pct": clearance_pct,
                        "status": "VIABLE" if margin_db >= 0 else "NOT VIABLE",
                        "tx_height": tx_h_eff,
                        "rx_height": rx_h_eff,
                    })
                except Exception as exc:
                    logger.warning("Skipping TX(%.5f,%.5f)→RX(%.5f,%.5f): %s", tx_lat, tx_lon, rx_lat, rx_lon, exc)
                    count += 1
                    continue

                count += 1
                if count % 100 == 0 or count == total:
                    feedback.setProgress(20 + int(60 * count / max(total, 1)))

        if rank_by == 0:
            results.sort(key=lambda r: (r["margin_db"], r["clearance_pct"]), reverse=True)
        elif rank_by == 1:
            results.sort(key=lambda r: (r["itm_loss_db"], r["margin_db"]))
        else:
            results.sort(key=lambda r: (r["clearance_pct"], r["margin_db"]), reverse=True)

        feedback.pushInfo("")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo("BATCH P2P RESULTS")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo("Total links computed: {}".format(len(results)))
        viable = sum(1 for r in results if r["status"] == "VIABLE")
        feedback.pushInfo("Viable links: {} / {}".format(viable, len(results)))
        feedback.pushInfo("Top 5 ranked results:")
        for i, r in enumerate(results[:5]):
            feedback.pushInfo(
                "  {}. {} → ({:.5f}, {:.5f}): {:.2f} km, margin={:.1f} dB, {}".format(
                    i + 1,
                    "TX" if mode == 0 else "TX candidate",
                    r["rx_lat"],
                    r["rx_lon"],
                    r["dist_km"],
                    r["margin_db"],
                    r["status"],
                )
            )
        feedback.pushInfo("=" * 50)

        feedback.setProgress(85)

        _batch_tmp = None
        try:
            markers_dest = self.parameterAsFileOutput(parameters, self.OUTPUT_MARKERS, context)
            if markers_dest:
                markers_path = markers_dest
            else:
                _batch_tmp = tempfile.mkdtemp(prefix="nowires_batch_")
                markers_path = os.path.join(_batch_tmp, "batch_markers.gpkg")
                feedback.pushInfo(
                    "Temporary outputs are intentionally left on disk for QGIS layer loading: {}".format(
                        _batch_tmp
                    )
                )
            self._write_batch_marker_layer(markers_path, results, feedback, mode)

            from qgis.core import QgsVectorLayer
            marker_layer = QgsVectorLayer(markers_path, "Batch P2P Markers")
            queue_layer_for_loading(context, marker_layer, "Batch P2P Markers")

            csv_path = self.parameterAsFileOutput(parameters, self.OUTPUT_CSV, context)
            json_path = self.parameterAsFileOutput(parameters, self.OUTPUT_JSON, context)

            if csv_path:
                self._write_batch_csv(csv_path, results, mode)
            if json_path:
                self._write_batch_json(json_path, results, parameters, context, mode)

            feedback.setProgress(100)

            output = {}
            if markers_path:
                output[self.OUTPUT_MARKERS] = markers_path
            if csv_path:
                output[self.OUTPUT_CSV] = csv_path
            if json_path:
                output[self.OUTPUT_JSON] = json_path

            return output
        finally:
            if _batch_tmp is not None:
                pass

    def _write_batch_marker_layer(self, path, results, feedback, mode):
        driver = ogr.GetDriverByName(ogr_driver_for_path(path))
        _remove_existing_ogr_dataset(driver, path)
        ds = driver.CreateDataSource(str(path))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        layer = ds.CreateLayer("batch_markers", srs=srs, geom_type=ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("rank", ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn("point_id", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("margin_db", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("loss_db", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("itm_loss_db", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("dist_km", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("clearance_pct", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("status", ogr.OFTString))
        layer.CreateField(ogr.FieldDefn("tx_lat", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("tx_lon", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("rx_lat", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("rx_lon", ogr.OFTReal))

        for rank, r in enumerate(results, 1):
            feat = ogr.Feature(layer.GetLayerDefn())
            if mode == 1:
                geom = ogr.Geometry(ogr.wkbPoint)
                geom.AddPoint(r["tx_lon"], r["tx_lat"])
                point_id = "TX({}, {:.5f}, {:.5f})".format(rank, r["tx_lat"], r["tx_lon"])
            else:
                geom = ogr.Geometry(ogr.wkbPoint)
                geom.AddPoint(r["rx_lon"], r["rx_lat"])
                point_id = "RX({}, {:.5f}, {:.5f})".format(rank, r["rx_lat"], r["rx_lon"])
            feat.SetGeometry(geom)
            feat.SetField("rank", rank)
            feat.SetField("point_id", point_id)
            feat.SetField("margin_db", r["margin_db"])
            feat.SetField("loss_db", r["total_loss_db"])
            feat.SetField("itm_loss_db", r["itm_loss_db"])
            feat.SetField("dist_km", round(r["dist_km"], 3))
            feat.SetField("clearance_pct", round(r["clearance_pct"], 1))
            feat.SetField("status", r["status"])
            feat.SetField("tx_lat", r["tx_lat"])
            feat.SetField("tx_lon", r["tx_lon"])
            feat.SetField("rx_lat", r["rx_lat"])
            feat.SetField("rx_lon", r["rx_lon"])
            layer.CreateFeature(feat)
            feat = None

        ds = None
        feedback.pushInfo("Wrote ranked marker layer to: {}".format(path))

    def _write_batch_csv(self, path, results, mode):
        import csv
        with open(str(path), "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            headers = ["Point ID", "rank", "tx_lat", "tx_lon", "rx_lat", "rx_lon",
                       "dist_km", "itm_loss_db", "total_loss_db",
                       "margin_db", "clearance_pct", "status"]
            writer.writerow(headers)
            for rank, r in enumerate(results, 1):
                if mode == 1:
                    point_id = "TX({}, {:.5f}, {:.5f})".format(rank, r["tx_lat"], r["tx_lon"])
                else:
                    point_id = "RX({}, {:.5f}, {:.5f})".format(rank, r["rx_lat"], r["rx_lon"])
                writer.writerow([
                    point_id,
                    rank,
                    r["tx_lat"],
                    r["tx_lon"],
                    r["rx_lat"],
                    r["rx_lon"],
                    round(r["dist_km"], 3),
                    round(r["itm_loss_db"], 2),
                    round(r["total_loss_db"], 2),
                    round(r["margin_db"], 2),
                    round(r["clearance_pct"], 1),
                    r["status"],
                ])

    def _write_batch_json(self, path, results, parameters, context, mode):
        import json
        payload = {
            "report_type": "batch_p2p",
            "generated_by": "NoWires",
            "mode": BATCH_MODE_OPTIONS[mode],
            "total_links": len(results),
            "viable_links": sum(1 for r in results if r["status"] == "VIABLE"),
            "results": [
                {
                    "rank": rank,
                    "tx_lat": r["tx_lat"],
                    "tx_lon": r["tx_lon"],
                    "rx_lat": r["rx_lat"],
                    "rx_lon": r["rx_lon"],
                    "distance_km": round(r["dist_km"], 3),
                    "itm_loss_db": round(r["itm_loss_db"], 2),
                    "total_loss_db": round(r["total_loss_db"], 2),
                    "margin_db": round(r["margin_db"], 2),
                    "clearance_pct": round(r["clearance_pct"], 1),
                    "status": r["status"],
                }
                for rank, r in enumerate(results, 1)
            ],
        }
        with open(str(path), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")

    def shortHelpString(self):
        return (
            "Batch point-to-point link analysis supporting two modes:\n"
            "- One-to-Many: single TX to multiple RX points from a vector layer\n"
            "- Many-to-One: multiple candidate TX sites to a single RX point\n"
            "Results are ranked by link margin, path loss, or Fresnel clearance."
        )

    def name(self):
        return "batch_p2p_analysis"

    def displayName(self):
        return self.tr("Batch P2P Analysis")

    def group(self):
        return self.tr("Radio Propagation")

    def groupId(self):
        return "radio_propagation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return BatchAnalysisAlgorithm()
