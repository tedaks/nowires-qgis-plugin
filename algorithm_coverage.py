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


Coverage Analysis Algorithm.

Computes ITM-based signal strength coverage over a grid area and
outputs a color-coded raster layer in QGIS.

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

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    Qgis,
    QgsColorRampShader,
    QgsLayerTreeLayer,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)
from osgeo import gdal, osr

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid, haversine_m
from .coverage_legend import show_coverage_legend
from .coverage_palette import build_heatmap_stops
from .coverage_summary import summarize_coverage_grid
from .coverage_compute import DEFAULT_MAX_PROFILE_PTS, coverage_profile_step_m
from .coverage_engine import compute_coverage
from .antenna import ANTENNA_PRESET_OPTIONS
from .clutter import (
    CLUTTER_MODEL_OPTIONS,
    CLUTTER_OVERRIDE_OPTIONS,
    LandCoverGrid,
    clutter_override_value,
    ensure_clutter_grid_for_area,
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
    validate_itm_input_ranges,
)
from .report_export import write_report_csv, write_report_html, write_report_json
from .report_payloads import (
    build_coverage_report_payload,
    build_empty_coverage_report_payload,
)

GRID_SIZE_PRESETS = [64, 128, 192, 256, 384, 512, 768, 1024]
POLARIZATION_NAMES = {0: "Horizontal", 1: "Vertical"}
METERS_PER_DEGREE_LAT = 111320.0


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


class CoverageAlgorithm(QgsProcessingAlgorithm):
    """Coverage analysis heatmap prediction."""

    TX_POINT = "TX_POINT"
    AREA = "AREA"
    TX_HEIGHT = "TX_HEIGHT"
    RX_HEIGHT = "RX_HEIGHT"
    FREQ_MHZ = "FREQ_MHZ"
    RADIUS_KM = "RADIUS_KM"
    GRID_SIZE = "GRID_SIZE"
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
    ANTENNA_BW = "ANTENNA_BW"
    ANTENNA_AZ = "ANTENNA_AZ"
    ANTENNA_PRESET = "ANTENNA_PRESET"
    FRONT_BACK_DB = "FRONT_BACK_DB"
    DOWNTILT_DEG = "DOWNTILT_DEG"
    H_PATTERN = "H_PATTERN"
    V_PATTERN = "V_PATTERN"
    CLUTTER_MODEL = "CLUTTER_MODEL"
    CLUTTER_RASTER = "CLUTTER_RASTER"
    TX_CLUTTER_OVERRIDE = "TX_CLUTTER_OVERRIDE"
    RX_CLUTTER_OVERRIDE = "RX_CLUTTER_OVERRIDE"
    N0 = "N0"
    EPSILON = "EPSILON"
    SIGMA = "SIGMA"
    OUTPUT_RASTER = "OUTPUT_RASTER"
    OUTPUT_REPORT_CSV = "OUTPUT_REPORT_CSV"
    OUTPUT_REPORT_JSON = "OUTPUT_REPORT_JSON"
    OUTPUT_REPORT_HTML = "OUTPUT_REPORT_HTML"

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterPoint(self.TX_POINT, "Transmitter (TX) point")
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
            QgsProcessingParameterNumber(
                self.RADIUS_KM,
                "Max analysis distance (km)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=50.0,
                minValue=1.0,
                maxValue=500.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.GRID_SIZE,
                "Grid size resolution",
                options=[
                    "64 x 64",
                    "128 x 128",
                    "192 x 192",
                    "256 x 256",
                    "384 x 384",
                    "512 x 512",
                    "768 x 768",
                    "1024 x 1024",
                ],
                defaultValue=2,
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
            QgsProcessingParameterNumber(
                self.ANTENNA_AZ,
                "Antenna azimuth (deg, blank=omni)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
                maxValue=360.0,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ANTENNA_BW,
                "Antenna beamwidth (deg)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=360.0,
                minValue=1.0,
                maxValue=360.0,
            )
        )
        self.addParameter(QgsProcessingParameterEnum(
            self.ANTENNA_PRESET, "TX antenna preset",
            options=ANTENNA_PRESET_OPTIONS, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.FRONT_BACK_DB, "TX front-to-back ratio (dB)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=25.0, minValue=0.0,
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.DOWNTILT_DEG, "TX downtilt (deg)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.0, minValue=-45.0, maxValue=45.0,
        ))
        self.addParameter(QgsProcessingParameterFile(
            self.H_PATTERN, "TX horizontal pattern CSV",
            extension="csv", optional=True,
        ))
        self.addParameter(QgsProcessingParameterFile(
            self.V_PATTERN, "TX vertical pattern CSV",
            extension="csv", optional=True,
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
                self.OUTPUT_RASTER,
                "Coverage raster output",
                "GeoTIFF files (*.tif)",
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_CSV,
                "Coverage report CSV",
                "CSV files (*.csv)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_JSON,
                "Coverage report JSON",
                "JSON files (*.json)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_HTML,
                "Coverage report HTML",
                "HTML files (*.html)",
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem

        tx_point = self.parameterAsPoint(
            parameters,
            self.TX_POINT,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        if tx_point is None:
            raise ValueError("TX point is required.")

        tx_lat = tx_point.y()
        tx_lon = tx_point.x()

        tx_h = self.parameterAsDouble(parameters, self.TX_HEIGHT, context)
        rx_h = self.parameterAsDouble(parameters, self.RX_HEIGHT, context)
        f_mhz = self.parameterAsDouble(parameters, self.FREQ_MHZ, context)
        radius_km = self.parameterAsDouble(parameters, self.RADIUS_KM, context)
        grid_size_index = self.parameterAsEnum(parameters, self.GRID_SIZE, context)
        grid_size = GRID_SIZE_PRESETS[grid_size_index]
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
        antenna_bw = self.parameterAsDouble(parameters, self.ANTENNA_BW, context)

        # Azimuth handling: None means omni when either unset or beamwidth is 360
        antenna_az = None
        if antenna_bw < 360.0:
            # Directional antenna: honour the azimuth if set, default to 0° if blank
            antenna_az = self.parameterAsDouble(parameters, self.ANTENNA_AZ, context)

        antenna_preset = self.parameterAsEnum(parameters, self.ANTENNA_PRESET, context)
        front_back_db = self.parameterAsDouble(parameters, self.FRONT_BACK_DB, context)
        downtilt_deg = self.parameterAsDouble(parameters, self.DOWNTILT_DEG, context)
        h_pattern = self.parameterAsFile(parameters, self.H_PATTERN, context)
        v_pattern = self.parameterAsFile(parameters, self.V_PATTERN, context)
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

        antenna_bw_override = (
            None
            if antenna_preset != 4 and antenna_bw == 360.0
            else antenna_bw
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

        feedback.pushInfo(
            "TX: ({:.5f}, {:.5f}), F={:.1f} MHz, R={:.1f} km, Grid={}x{}".format(
                tx_lat, tx_lon, f_mhz, radius_km, grid_size, grid_size
            )
        )
        feedback.pushInfo(
            "Clutter correction: {}".format(
                CLUTTER_MODEL_OPTIONS[1] if clutter_enabled else CLUTTER_MODEL_OPTIONS[0]
            )
        )
        feedback.pushInfo(
            "TX antenna preset: {}".format(ANTENNA_PRESET_OPTIONS[antenna_preset])
        )

        # Compute padded DEM area
        pad_deg = max(0.05, radius_km / (METERS_PER_DEGREE_LAT / 1000.0) * 0.1)
        radius_deg_lat = radius_km / (METERS_PER_DEGREE_LAT / 1000.0)
        radius_deg_lon = radius_km / (
            METERS_PER_DEGREE_LAT / 1000.0 * max(math.cos(math.radians(tx_lat)), 0.01)
        )
        south = tx_lat - radius_deg_lat - pad_deg
        north = tx_lat + radius_deg_lat + pad_deg
        west = tx_lon - radius_deg_lon - pad_deg
        east = tx_lon + radius_deg_lon + pad_deg

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise RuntimeError("Failed to obtain DEM data for the coverage area.")

        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(15)
        elev = ElevationGrid(dem_path)

        if clutter_grid is None and clutter_enabled:
            clutter_grid = ensure_clutter_grid_for_area(
                south=south,
                north=north,
                west=west,
                east=east,
                feedback=feedback,
            )

        feedback.pushInfo("Computing coverage...")
        feedback.setProgress(20)

        result = compute_coverage(
            elev_grid=elev,
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            tx_h_m=tx_h,
            rx_h_m=rx_h,
            f_mhz=f_mhz,
            grid_size=grid_size,
            radius_km=radius_km,
            profile_step_m=coverage_profile_step_m(f_mhz),
            max_profile_pts=DEFAULT_MAX_PROFILE_PTS,
            tx_power_dbm=tx_power,
            tx_gain_dbi=tx_gain,
            rx_gain_dbi=rx_gain,
            cable_loss_db=cable_loss,
            rx_sensitivity_dbm=rx_sens,
            antenna_az_deg=antenna_az,
            antenna_beamwidth_deg=antenna_bw_override,
            polarization=polarization,
            climate=climate,
            N0=n0,
            epsilon=epsilon,
            sigma=sigma,
            time_pct=time_pct,
            location_pct=location_pct,
            situation_pct=situation_pct,
            antenna_preset=antenna_preset,
            antenna_front_back_db=front_back_db,
            antenna_downtilt_deg=downtilt_deg,
            antenna_horizontal_pattern_path=h_pattern,
            antenna_vertical_pattern_path=v_pattern,
            clutter_enabled=clutter_enabled,
            clutter_grid=clutter_grid,
            tx_clutter_override=tx_clutter_override,
            rx_clutter_override=rx_clutter_override,
            feedback=feedback,
        )

        (
            prx_grid,
            loss_grid,
            min_lat,
            max_lat,
            min_lon,
            max_lon,
            itm_loss_grid,
            clutter_loss_grid,
        ) = result

        if prx_grid is None:
            raise RuntimeError("Coverage computation was cancelled.")

        feedback.pushInfo("Writing coverage raster...")
        feedback.setProgress(85)

        # Write GeoTIFF
        tif_dest = self.parameterAsFileOutput(parameters, self.OUTPUT_RASTER, context)
        tif_path = (
            tif_dest
            if tif_dest
            else os.path.join(
                tempfile.mkdtemp(prefix="nowires_coverage_"), "coverage_prx.tif"
            )
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

        driver = gdal.GetDriverByName("GTiff")
        n_rows, n_cols = prx_grid.shape
        ds = driver.Create(tif_path, n_cols, n_rows, 1, gdal.GDT_Float32)
        ds.SetGeoTransform(
            [
                min_lon,
                (max_lon - min_lon) / n_cols,
                0,
                max_lat,
                0,
                -(max_lat - min_lat) / n_rows,
            ]
        )
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(-9999.0)
        # Flip vertically since geo transform starts at top
        band.WriteArray(prx_grid[::-1])
        band.FlushCache()
        ds = None

        # Load as QGIS raster layer with color ramp
        layer_name = "Coverage ({:.0f} MHz, {:.0f} km, {}x{})".format(
            f_mhz, radius_km, grid_size, grid_size
        )
        raster_layer = QgsRasterLayer(tif_path, layer_name)

        if raster_layer.isValid():
            self._apply_coverage_style(raster_layer, rx_sens)
            raster_layer.setOpacity(1.0)

            dem_layer = QgsRasterLayer(dem_path, "NoWires DEM (GLO-30)")
            if dem_layer.isValid():
                elev_props = dem_layer.elevationProperties()
                elev_props.setEnabled(True)
                elev_props.setMode(Qgis.RasterElevationMode.RepresentsElevationSurface)
                elev_props.setBandNumber(1)
                _queue_layer_for_loading(context, dem_layer, "NoWires DEM (GLO-30)")
                self._raster_layer_ids.append(dem_layer.id())
                QgsProject.instance().writeEntry(
                    "NoWires", "last_dem_layer_id", dem_layer.id()
                )

            _queue_layer_for_loading(context, raster_layer, layer_name)
            QgsProject.instance().writeEntry(
                "NoWires", "last_coverage_layer_id", raster_layer.id()
            )
            show_coverage_legend(rx_sensitivity_dbm=rx_sens)

            # Statistics
            raster_grid = prx_grid[::-1]
            valid = ~np.isnan(raster_grid)
            if not valid.any():
                report_payload = build_empty_coverage_report_payload(
                    tx_lat=tx_lat,
                    tx_lon=tx_lon,
                    tx_h=tx_h,
                    rx_h=rx_h,
                    f_mhz=f_mhz,
                    radius_km=radius_km,
                    grid_size=grid_size,
                    polarization_name=POLARIZATION_NAMES.get(
                        polarization, str(polarization)
                    ),
                    climate_name=CLIMATE_NAMES.get(climate, str(climate)),
                    time_pct=time_pct,
                    location_pct=location_pct,
                    situation_pct=situation_pct,
                    tx_power=tx_power,
                    tx_gain=tx_gain,
                    rx_gain=rx_gain,
                    cable_loss=cable_loss,
                    rx_sensitivity_dbm=rx_sens,
                    pixel_count=int(raster_grid.size),
                    clutter_model=CLUTTER_MODEL_OPTIONS[1] if clutter_enabled else CLUTTER_MODEL_OPTIONS[0],
                    clutter_source=clutter_raster_path or ("override" if tx_clutter_override or rx_clutter_override else "off"),
                    tx_antenna_preset=ANTENNA_PRESET_OPTIONS[antenna_preset],
                )
                feedback.pushInfo("")
                feedback.pushInfo("=" * 40)
                feedback.pushInfo("COVERAGE RESULTS")
                feedback.pushInfo("=" * 40)
                feedback.pushInfo(
                    "Valid pixels: 0 / {}".format(raster_grid.size)
                )
                feedback.pushInfo("No valid coverage cells were computed.")
                feedback.pushInfo(
                    "Availability method: {}".format(
                        report_payload["results"]["availability_method"]
                    )
                )
                feedback.pushInfo(
                    "Reliability: {}".format(
                        report_payload["results"]["reliability_summary"]
                    )
                )
                feedback.pushInfo(
                    "Fade margin class: {}".format(
                        report_payload["results"]["fade_margin_class"]
                    )
                )
                feedback.pushInfo("=" * 40)
            else:
                pct_above = (
                    float((raster_grid[valid] >= rx_sens).sum())
                    / max(valid.sum(), 1)
                    * 100
                )
                summary = summarize_coverage_grid(
                    prx_grid=raster_grid,
                    tx_lat=tx_lat,
                    tx_lon=tx_lon,
                    min_lat=min_lat,
                    max_lat=max_lat,
                    min_lon=min_lon,
                    max_lon=max_lon,
                    rx_sensitivity_dbm=rx_sens,
                )
                report_payload = build_coverage_report_payload(
                    tx_lat=tx_lat,
                    tx_lon=tx_lon,
                    tx_h=tx_h,
                    rx_h=rx_h,
                    f_mhz=f_mhz,
                    radius_km=radius_km,
                    grid_size=grid_size,
                    polarization_name=POLARIZATION_NAMES.get(
                        polarization, str(polarization)
                    ),
                    climate_name=CLIMATE_NAMES.get(climate, str(climate)),
                    time_pct=time_pct,
                    location_pct=location_pct,
                    situation_pct=situation_pct,
                    tx_power=tx_power,
                    tx_gain=tx_gain,
                    rx_gain=rx_gain,
                    cable_loss=cable_loss,
                    rx_sensitivity_dbm=rx_sens,
                    valid_pixel_count=int(valid.sum()),
                    pixel_count=int(raster_grid.size),
                    min_prx_dbm=float(np.nanmin(raster_grid)),
                    max_prx_dbm=float(np.nanmax(raster_grid)),
                    mean_prx_dbm=float(np.nanmean(raster_grid)),
                    pct_above_sensitivity=pct_above,
                    usable_cell_count=int(summary["usable_cell_count"]),
                    min_distance_km=summary["min_distance_km"],
                    max_distance_km=summary["max_distance_km"],
                    average_distance_km=summary["average_distance_km"],
                    clutter_model=CLUTTER_MODEL_OPTIONS[1] if clutter_enabled else CLUTTER_MODEL_OPTIONS[0],
                    clutter_source=clutter_raster_path or ("override" if tx_clutter_override or rx_clutter_override else "off"),
                    tx_antenna_preset=ANTENNA_PRESET_OPTIONS[antenna_preset],
                )
                feedback.pushInfo("")
                feedback.pushInfo("=" * 40)
                feedback.pushInfo("COVERAGE RESULTS")
                feedback.pushInfo("=" * 40)
                feedback.pushInfo(
                    "Valid pixels: {} / {}".format(int(valid.sum()), raster_grid.size)
                )
                feedback.pushInfo(
                    "Min Prx: {:.1f} dBm".format(float(np.nanmin(raster_grid)))
                )
                feedback.pushInfo(
                    "Max Prx: {:.1f} dBm".format(float(np.nanmax(raster_grid)))
                )
                feedback.pushInfo(
                    "Mean Prx: {:.1f} dBm".format(float(np.nanmean(raster_grid)))
                )
                feedback.pushInfo(
                    "Above sensitivity ({:.0f} dBm): {:.1f}%".format(rx_sens, pct_above)
                )
                feedback.pushInfo(
                    "Min usable distance: {:.2f} km".format(summary["min_distance_km"])
                )
                feedback.pushInfo(
                    "Max usable distance: {:.2f} km".format(summary["max_distance_km"])
                )
                feedback.pushInfo(
                    "Average usable distance: {:.2f} km".format(
                        summary["average_distance_km"]
                    )
                )
                feedback.pushInfo(
                    "Availability method: {}".format(
                        report_payload["results"]["availability_method"]
                    )
                )
                feedback.pushInfo(
                    "Reliability: {}".format(
                        report_payload["results"]["reliability_summary"]
                    )
                )
                feedback.pushInfo(
                    "Fade margin class: {}".format(
                        report_payload["results"]["fade_margin_class"]
                    )
                )
                if report_payload["results"]["availability_estimate_pct"] is not None:
                    feedback.pushInfo(
                        "Availability estimate: {:.2f}%".format(
                            report_payload["results"]["availability_estimate_pct"]
                        )
                )
                if summary["usable_cell_count"] == 0:
                    feedback.pushInfo("No cells met the RX sensitivity threshold.")
                feedback.pushInfo("=" * 40)
            if report_csv_path:
                write_report_csv(report_csv_path, report_payload)
            if report_json_path:
                write_report_json(report_json_path, report_payload)
            if report_html_path:
                write_report_html(
                    report_html_path,
                    report_payload,
                    title="NoWires Coverage Report",
                )
        else:
            feedback.pushInfo("Warning: Could not load coverage raster layer.")

        feedback.setProgress(100)
        return {
            self.OUTPUT_RASTER: tif_path,
            self.OUTPUT_REPORT_CSV: report_csv_path,
            self.OUTPUT_REPORT_JSON: report_json_path,
            self.OUTPUT_REPORT_HTML: report_html_path,
        }

    def _apply_coverage_style(self, layer, rx_sensitivity_dbm):
        """Apply a color ramp renderer based on signal level thresholds."""
        provider = layer.dataProvider()

        entries = []
        for value, rgba, label in build_heatmap_stops():
            entry = QgsColorRampShader.ColorRampItem()
            entry.value = value
            from qgis.PyQt.QtGui import QColor

            entry.color = QColor(rgba[0], rgba[1], rgba[2], rgba[3])
            entry.label = "{} ({:.0f} dBm)".format(label, value)
            entries.append(entry)

        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
        color_ramp_shader.setColorRampItemList(entries)

        shader = QgsRasterShader()
        shader.setRasterShaderFunction(color_ramp_shader)

        renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def postProcessAlgorithm(self, context, feedback):
        root = QgsProject.instance().layerTreeRoot()
        for layer_id in self._raster_layer_ids:
            node = root.findLayer(layer_id)
            if node is not None:
                clone = node.clone()
                parent = node.parent()
                parent.removeChildNode(node)
                parent.insertChildNode(0, clone)
        return {}

    def name(self):
        return "coverage_analysis"

    def displayName(self):
        return self.tr("Coverage Analysis")

    def group(self):
        return self.tr("Radio Propagation")

    def groupId(self):
        return "radio_propagation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return CoverageAlgorithm()
