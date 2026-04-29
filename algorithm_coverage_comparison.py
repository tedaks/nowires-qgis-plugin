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
    QgsColorRampShader,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsRasterLayer,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)
from osgeo import gdal, osr

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid
from .coverage_engine import compute_coverage
from .coverage_compute import (
    DEFAULT_MAX_PROFILE_PTS,
    coverage_profile_step_m,
    grid_to_raster_array,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .processing_utils import queue_layer_for_loading
from .clutter import (
    CLUTTER_MODEL_OPTIONS,
    CLUTTER_OVERRIDE_OPTIONS,
    LandCoverGrid,
    clutter_source_label,
    clutter_override_value,
    compute_terminal_clutter_losses,
    ensure_clutter_grid_for_area,
)
from .radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_N0,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MIN_SIGMA,
    validate_itm_input_ranges,
)

GRID_SIZE_PRESETS = [64, 128, 192, 256, 384, 512, 768, 1024]
POLARIZATION_NAMES = {0: "Horizontal", 1: "Vertical"}
METERS_PER_DEGREE_LAT = 111320.0

DELTA_STYLE_OPTIONS = ["diverging", "threshold"]
DELTA_THRESHOLD_DEFAULTS = [3.0, 5.0, 10.0]


class CoverageComparisonAlgorithm(QgsProcessingAlgorithm):
    """Dual-panel coverage comparison with delta raster output."""

    PANEL_A_POINT = "PANEL_A_POINT"
    PANEL_A_TX_HEIGHT = "PANEL_A_TX_HEIGHT"
    PANEL_A_RX_HEIGHT = "PANEL_A_RX_HEIGHT"
    PANEL_A_FREQ_MHZ = "PANEL_A_FREQ_MHZ"
    PANEL_A_RADIUS_KM = "PANEL_A_RADIUS_KM"
    PANEL_A_GRID_SIZE = "PANEL_A_GRID_SIZE"
    PANEL_A_POLARIZATION = "PANEL_A_POLARIZATION"
    PANEL_A_CLIMATE = "PANEL_A_CLIMATE"
    PANEL_A_TIME_PCT = "PANEL_A_TIME_PCT"
    PANEL_A_LOCATION_PCT = "PANEL_A_LOCATION_PCT"
    PANEL_A_SITUATION_PCT = "PANEL_A_SITUATION_PCT"
    PANEL_A_TX_POWER = "PANEL_A_TX_POWER"
    PANEL_A_TX_GAIN = "PANEL_A_TX_GAIN"
    PANEL_A_RX_GAIN = "PANEL_A_RX_GAIN"
    PANEL_A_CABLE_LOSS = "PANEL_A_CABLE_LOSS"
    PANEL_A_RX_SENSITIVITY = "PANEL_A_RX_SENSITIVITY"
    PANEL_A_ANTENNA_BW = "PANEL_A_ANTENNA_BW"
    PANEL_A_ANTENNA_AZ = "PANEL_A_ANTENNA_AZ"
    PANEL_A_ANTENNA_PRESET = "PANEL_A_ANTENNA_PRESET"
    PANEL_A_FRONT_BACK_DB = "PANEL_A_FRONT_BACK_DB"
    PANEL_A_DOWNTILT_DEG = "PANEL_A_DOWNTILT_DEG"
    PANEL_A_H_PATTERN = "PANEL_A_H_PATTERN"
    PANEL_A_V_PATTERN = "PANEL_A_V_PATTERN"
    PANEL_A_CLUTTER_MODEL = "PANEL_A_CLUTTER_MODEL"
    PANEL_A_CLUTTER_RASTER = "PANEL_A_CLUTTER_RASTER"
    PANEL_A_TX_CLUTTER_OVERRIDE = "PANEL_A_TX_CLUTTER_OVERRIDE"
    PANEL_A_RX_CLUTTER_OVERRIDE = "PANEL_A_RX_CLUTTER_OVERRIDE"
    PANEL_A_N0 = "PANEL_A_N0"
    PANEL_A_EPSILON = "PANEL_A_EPSILON"
    PANEL_A_SIGMA = "PANEL_A_SIGMA"

    PANEL_B_POINT = "PANEL_B_POINT"
    PANEL_B_TX_HEIGHT = "PANEL_B_TX_HEIGHT"
    PANEL_B_RX_HEIGHT = "PANEL_B_RX_HEIGHT"
    PANEL_B_FREQ_MHZ = "PANEL_B_FREQ_MHZ"
    PANEL_B_RADIUS_KM = "PANEL_B_RADIUS_KM"
    PANEL_B_GRID_SIZE = "PANEL_B_GRID_SIZE"
    PANEL_B_POLARIZATION = "PANEL_B_POLARIZATION"
    PANEL_B_CLIMATE = "PANEL_B_CLIMATE"
    PANEL_B_TIME_PCT = "PANEL_B_TIME_PCT"
    PANEL_B_LOCATION_PCT = "PANEL_B_LOCATION_PCT"
    PANEL_B_SITUATION_PCT = "PANEL_B_SITUATION_PCT"
    PANEL_B_TX_POWER = "PANEL_B_TX_POWER"
    PANEL_B_TX_GAIN = "PANEL_B_TX_GAIN"
    PANEL_B_RX_GAIN = "PANEL_B_RX_GAIN"
    PANEL_B_CABLE_LOSS = "PANEL_B_CABLE_LOSS"
    PANEL_B_RX_SENSITIVITY = "PANEL_B_RX_SENSITIVITY"
    PANEL_B_ANTENNA_BW = "PANEL_B_ANTENNA_BW"
    PANEL_B_ANTENNA_AZ = "PANEL_B_ANTENNA_AZ"
    PANEL_B_ANTENNA_PRESET = "PANEL_B_ANTENNA_PRESET"
    PANEL_B_FRONT_BACK_DB = "PANEL_B_FRONT_BACK_DB"
    PANEL_B_DOWNTILT_DEG = "PANEL_B_DOWNTILT_DEG"
    PANEL_B_H_PATTERN = "PANEL_B_H_PATTERN"
    PANEL_B_V_PATTERN = "PANEL_B_V_PATTERN"
    PANEL_B_CLUTTER_MODEL = "PANEL_B_CLUTTER_MODEL"
    PANEL_B_CLUTTER_RASTER = "PANEL_B_CLUTTER_RASTER"
    PANEL_B_TX_CLUTTER_OVERRIDE = "PANEL_B_TX_CLUTTER_OVERRIDE"
    PANEL_B_RX_CLUTTER_OVERRIDE = "PANEL_B_RX_CLUTTER_OVERRIDE"
    PANEL_B_N0 = "PANEL_B_N0"
    PANEL_B_EPSILON = "PANEL_B_EPSILON"
    PANEL_B_SIGMA = "PANEL_B_SIGMA"

    OUTPUT_DIR = "OUTPUT_DIR"
    DELTA_STYLE = "DELTA_STYLE"
    DELTA_THRESHOLD_DB = "DELTA_THRESHOLD_DB"
    OUTPUT_A = "OUTPUT_A"
    OUTPUT_B = "OUTPUT_B"
    OUTPUT_DELTA = "OUTPUT_DELTA"
    OUTPUT_REPORT_HTML = "OUTPUT_REPORT_HTML"

    def __init__(self):
        super().__init__()
        self._raster_layer_ids = []

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def _add_panel_params(self, prefix, config):
        self.addParameter(
            config["point_param"](
                f"{prefix}_POINT", f"Panel {prefix.split('_')[1]} Transmitter (TX) point"
            )
        )
        self.addParameter(
            config["height_param"](
                f"{prefix}_TX_HEIGHT",
                f"Panel {prefix.split('_')[1]} TX antenna height (m)",
                defaultValue=30.0,
            )
        )
        self.addParameter(
            config["height_param"](
                f"{prefix}_RX_HEIGHT",
                f"Panel {prefix.split('_')[1]} RX antenna height (m)",
                defaultValue=10.0,
            )
        )
        self.addParameter(
            config["freq_param"](
                f"{prefix}_FREQ_MHZ",
                f"Panel {prefix.split('_')[1]} Frequency (MHz)",
                defaultValue=300.0,
            )
        )
        self.addParameter(
            config["radius_param"](
                f"{prefix}_RADIUS_KM",
                f"Panel {prefix.split('_')[1]} Max analysis distance (km)",
                defaultValue=50.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                f"{prefix}_GRID_SIZE",
                f"Panel {prefix.split('_')[1]} Grid size resolution",
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
                f"{prefix}_POLARIZATION",
                f"Panel {prefix.split('_')[1]} Polarization",
                options=["Horizontal", "Vertical"],
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                f"{prefix}_CLIMATE",
                f"Panel {prefix.split('_')[1]} Climate zone",
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
            config["pct_param"](
                f"{prefix}_TIME_PCT",
                f"Panel {prefix.split('_')[1]} Time percentage",
                defaultValue=50.0,
            )
        )
        self.addParameter(
            config["pct_param"](
                f"{prefix}_LOCATION_PCT",
                f"Panel {prefix.split('_')[1]} Location percentage",
                defaultValue=50.0,
            )
        )
        self.addParameter(
            config["pct_param"](
                f"{prefix}_SITUATION_PCT",
                f"Panel {prefix.split('_')[1]} Situation percentage",
                defaultValue=50.0,
            )
        )
        self.addParameter(
            config["dbm_param"](
                f"{prefix}_TX_POWER",
                f"Panel {prefix.split('_')[1]} TX power (dBm)",
                defaultValue=43.0,
            )
        )
        self.addParameter(
            config["db_param"](
                f"{prefix}_TX_GAIN",
                f"Panel {prefix.split('_')[1]} TX antenna gain (dBi)",
                defaultValue=8.0,
            )
        )
        self.addParameter(
            config["db_param"](
                f"{prefix}_RX_GAIN",
                f"Panel {prefix.split('_')[1]} RX antenna gain (dBi)",
                defaultValue=2.0,
            )
        )
        self.addParameter(
            config["loss_param"](
                f"{prefix}_CABLE_LOSS",
                f"Panel {prefix.split('_')[1]} Cable loss (dB)",
                defaultValue=2.0,
            )
        )
        self.addParameter(
            config["dbm_param"](
                f"{prefix}_RX_SENSITIVITY",
                f"Panel {prefix.split('_')[1]} RX sensitivity (dBm)",
                defaultValue=-100.0,
            )
        )
        self.addParameter(
            config["az_param"](
                f"{prefix}_ANTENNA_AZ",
                f"Panel {prefix.split('_')[1]} Antenna azimuth (deg, blank=omni)",
                defaultValue=0.0,
                optional=True,
            )
        )
        self.addParameter(
            config["bw_param"](
                f"{prefix}_ANTENNA_BW",
                f"Panel {prefix.split('_')[1]} Antenna beamwidth (deg)",
                defaultValue=360.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                f"{prefix}_ANTENNA_PRESET",
                f"Panel {prefix.split('_')[1]} TX antenna preset",
                options=ANTENNA_PRESET_OPTIONS,
                defaultValue=0,
            )
        )
        self.addParameter(
            config["db_param"](
                f"{prefix}_FRONT_BACK_DB",
                f"Panel {prefix.split('_')[1]} TX front-to-back ratio (dB)",
                defaultValue=25.0,
            )
        )
        self.addParameter(
            config["downtilt_param"](
                f"{prefix}_DOWNTILT_DEG",
                f"Panel {prefix.split('_')[1]} TX downtilt (deg)",
                defaultValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                f"{prefix}_H_PATTERN",
                f"Panel {prefix.split('_')[1]} TX horizontal pattern CSV",
                extension="csv",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                f"{prefix}_V_PATTERN",
                f"Panel {prefix.split('_')[1]} TX vertical pattern CSV",
                extension="csv",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                f"{prefix}_CLUTTER_MODEL",
                f"Panel {prefix.split('_')[1]} Clutter correction",
                options=CLUTTER_MODEL_OPTIONS,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                f"{prefix}_CLUTTER_RASTER",
                f"Panel {prefix.split('_')[1]} Land-cover raster (auto-downloaded if blank)",
                extension="tif",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                f"{prefix}_TX_CLUTTER_OVERRIDE",
                f"Panel {prefix.split('_')[1]} TX clutter override",
                options=CLUTTER_OVERRIDE_OPTIONS,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                f"{prefix}_RX_CLUTTER_OVERRIDE",
                f"Panel {prefix.split('_')[1]} RX clutter override",
                options=CLUTTER_OVERRIDE_OPTIONS,
                defaultValue=0,
            )
        )
        n0_param = config["n0_param"](
            f"{prefix}_N0",
            f"Panel {prefix.split('_')[1]} Surface refractivity N0 (N-units)",
            defaultValue=301.0,
        )
        n0_param.setFlags(n0_param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        self.addParameter(n0_param)

        epsilon_param = config["epsilon_param"](
            f"{prefix}_EPSILON",
            f"Panel {prefix.split('_')[1]} Earth permittivity (epsilon)",
            defaultValue=15.0,
        )
        epsilon_param.setFlags(
            epsilon_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
        )
        self.addParameter(epsilon_param)

        sigma_param = config["sigma_param"](
            f"{prefix}_SIGMA",
            f"Panel {prefix.split('_')[1]} Earth conductivity (sigma, S/m)",
            defaultValue=0.005,
        )
        sigma_param.setFlags(
            sigma_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
        )
        self.addParameter(sigma_param)

    def initAlgorithm(self, config):
        panel_config = {
            "point_param": lambda name, desc: QgsProcessingParameterPoint(name, desc),
            "height_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                **kw
            ),
            "freq_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ,
                **kw
            ),
            "radius_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=1.0, maxValue=500.0,
                **kw
            ),
            "pct_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=0.01, maxValue=99.99,
                **kw
            ),
            "dbm_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                **kw
            ),
            "db_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=0.0,
                **kw
            ),
            "loss_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=0.0,
                **kw
            ),
            "az_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=0.0, maxValue=360.0,
                **kw
            ),
            "bw_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=1.0, maxValue=360.0,
                **kw
            ),
            "downtilt_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=-45.0, maxValue=45.0,
                **kw
            ),
            "n0_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=ITM_MIN_N0, maxValue=ITM_MAX_N0,
                **kw
            ),
            "epsilon_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=1.0,
                **kw
            ),
            "sigma_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
                name, desc, type=QgsProcessingParameterNumber.Double,
                minValue=ITM_MIN_SIGMA,
                **kw
            ),
        }

        self._add_panel_params("PANEL_A", panel_config)
        self._add_panel_params("PANEL_B", panel_config)

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_DIR,
                "Output directory for coverage comparison files",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DELTA_STYLE,
                "Delta raster styling",
                options=DELTA_STYLE_OPTIONS,
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DELTA_THRESHOLD_DB,
                "Significant difference threshold (dB)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5.0,
                minValue=0.1,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_A,
                "Panel A coverage raster output",
                fileFilter="GeoTIFF files (*.tif)",
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_B,
                "Panel B coverage raster output",
                fileFilter="GeoTIFF files (*.tif)",
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_DELTA,
                "Delta raster output (A - B in dB)",
                fileFilter="GeoTIFF files (*.tif)",
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_REPORT_HTML,
                "Comparison report HTML",
                fileFilter="HTML files (*.html)",
                optional=True,
            )
        )

    def _run_panel_coverage(self, prefix, parameters, context, feedback, elev, south, north, west, east):
        """Run compute_coverage for one panel and return the result tuple."""
        from qgis.core import QgsCoordinateReferenceSystem

        tx_point = self.parameterAsPoint(
            parameters,
            f"{prefix}_POINT",
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        if tx_point is None:
            raise ValueError(f"{prefix} TX point is required.")

        tx_lat = tx_point.y()
        tx_lon = tx_point.x()

        tx_h = self.parameterAsDouble(parameters, f"{prefix}_TX_HEIGHT", context)
        rx_h = self.parameterAsDouble(parameters, f"{prefix}_RX_HEIGHT", context)
        f_mhz = self.parameterAsDouble(parameters, f"{prefix}_FREQ_MHZ", context)
        radius_km = self.parameterAsDouble(parameters, f"{prefix}_RADIUS_KM", context)
        grid_size_index = self.parameterAsEnum(parameters, f"{prefix}_GRID_SIZE", context)
        grid_size = GRID_SIZE_PRESETS[grid_size_index]
        polarization = self.parameterAsEnum(parameters, f"{prefix}_POLARIZATION", context)
        climate = self.parameterAsEnum(parameters, f"{prefix}_CLIMATE", context)
        time_pct = self.parameterAsDouble(parameters, f"{prefix}_TIME_PCT", context)
        location_pct = self.parameterAsDouble(parameters, f"{prefix}_LOCATION_PCT", context)
        situation_pct = self.parameterAsDouble(parameters, f"{prefix}_SITUATION_PCT", context)
        tx_power = self.parameterAsDouble(parameters, f"{prefix}_TX_POWER", context)
        tx_gain = self.parameterAsDouble(parameters, f"{prefix}_TX_GAIN", context)
        rx_gain = self.parameterAsDouble(parameters, f"{prefix}_RX_GAIN", context)
        cable_loss = self.parameterAsDouble(parameters, f"{prefix}_CABLE_LOSS", context)
        rx_sens = self.parameterAsDouble(parameters, f"{prefix}_RX_SENSITIVITY", context)
        antenna_bw = self.parameterAsDouble(parameters, f"{prefix}_ANTENNA_BW", context)

        antenna_az = None
        if antenna_bw < 360.0:
            antenna_az = self.parameterAsDouble(parameters, f"{prefix}_ANTENNA_AZ", context)

        antenna_preset = self.parameterAsEnum(parameters, f"{prefix}_ANTENNA_PRESET", context)
        front_back_db = self.parameterAsDouble(parameters, f"{prefix}_FRONT_BACK_DB", context)
        downtilt_deg = self.parameterAsDouble(parameters, f"{prefix}_DOWNTILT_DEG", context)
        h_pattern = self.parameterAsFile(parameters, f"{prefix}_H_PATTERN", context)
        v_pattern = self.parameterAsFile(parameters, f"{prefix}_V_PATTERN", context)
        clutter_enabled = self.parameterAsEnum(parameters, f"{prefix}_CLUTTER_MODEL", context) == 1
        clutter_raster_path = self.parameterAsFile(parameters, f"{prefix}_CLUTTER_RASTER", context)
        if clutter_raster_path:
            clutter_grid = LandCoverGrid.from_raster(clutter_raster_path)
        else:
            clutter_grid = None
        tx_clutter_override = clutter_override_value(
            self.parameterAsEnum(parameters, f"{prefix}_TX_CLUTTER_OVERRIDE", context)
        )
        rx_clutter_override = clutter_override_value(
            self.parameterAsEnum(parameters, f"{prefix}_RX_CLUTTER_OVERRIDE", context)
        )

        antenna_bw_override = (
            None
            if antenna_preset != 4 and antenna_bw == 360.0
            else antenna_bw
        )

        n0 = self.parameterAsDouble(parameters, f"{prefix}_N0", context)
        epsilon = self.parameterAsDouble(parameters, f"{prefix}_EPSILON", context)
        sigma = self.parameterAsDouble(parameters, f"{prefix}_SIGMA", context)

        validate_itm_input_ranges(
            tx_height_m=tx_h,
            rx_height_m=rx_h,
            frequency_mhz=f_mhz,
            surface_refractivity_n0=n0,
            earth_conductivity_sigma=sigma,
        )

        feedback.pushInfo(
            f"[{prefix}] TX: ({tx_lat:.5f}, {tx_lon:.5f}), F={f_mhz:.1f} MHz, R={radius_km:.1f} km, Grid={grid_size}x{grid_size}"
        )

        if clutter_grid is None and clutter_enabled:
            clutter_grid = ensure_clutter_grid_for_area(
                south=south,
                north=north,
                west=west,
                east=east,
                feedback=feedback,
            )

        clutter_source = clutter_source_label(
            enabled=clutter_enabled,
            land_cover_grid=clutter_grid,
            raster_path=clutter_raster_path,
            tx_override=tx_clutter_override,
            rx_override=rx_clutter_override,
        )
        tx_clutter_for_report = compute_terminal_clutter_losses(
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            rx_lat=tx_lat,
            rx_lon=tx_lon,
            frequency_mhz=f_mhz,
            enabled=clutter_enabled,
            land_cover_grid=clutter_grid,
            tx_override=tx_clutter_override,
            rx_override=rx_clutter_override,
        )

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

        return {
            "result": result,
            "clutter_source": clutter_source,
            "tx_clutter_for_report": tx_clutter_for_report,
            "clutter_enabled": clutter_enabled,
            "antenna_preset": antenna_preset,
            "tx_lat": tx_lat,
            "tx_lon": tx_lon,
            "tx_h": tx_h,
            "rx_h": rx_h,
            "f_mhz": f_mhz,
            "radius_km": radius_km,
            "grid_size": grid_size,
            "polarization": polarization,
            "time_pct": time_pct,
            "location_pct": location_pct,
            "situation_pct": situation_pct,
            "tx_power": tx_power,
            "tx_gain": tx_gain,
            "rx_gain": rx_gain,
            "cable_loss": cable_loss,
            "rx_sens": rx_sens,
        }

    def _write_coverage_raster(self, tif_path, prx_grid, min_lat, max_lat, min_lon, max_lon, rx_sens):
        """Write a coverage raster to GeoTIFF."""
        driver = gdal.GetDriverByName("GTiff")
        n_rows, n_cols = prx_grid.shape
        ds = driver.Create(tif_path, n_cols, n_rows, 1, gdal.GDT_Float32)
        if ds is None:
            raise QgsProcessingException("Failed to create GeoTIFF: {}".format(tif_path))
        try:
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
            band.WriteArray(grid_to_raster_array(prx_grid))
            band.FlushCache()
        finally:
            ds = None

    def _apply_delta_style(self, layer, threshold_db, style="diverging"):
        """Apply color ramp to delta raster. 'diverging' uses blue-white-red;
        'threshold' shows only three categories: improved, unchanged, degraded."""
        from qgis.PyQt.QtGui import QColor

        provider = layer.dataProvider()
        entries = []

        if style == "threshold":
            entries = [
                QgsColorRampShader.ColorRampItem(
                    -1e6, QColor(30, 80, 180), f"A better (<-{threshold_db:.0f} dB)"
                ),
                QgsColorRampShader.ColorRampItem(
                    -threshold_db, QColor(30, 80, 180), f"A better (<-{threshold_db:.0f} dB)"
                ),
                QgsColorRampShader.ColorRampItem(
                    -threshold_db + 0.001, QColor(240, 240, 240), "No change"
                ),
                QgsColorRampShader.ColorRampItem(
                    threshold_db - 0.001, QColor(240, 240, 240), "No change"
                ),
                QgsColorRampShader.ColorRampItem(
                    threshold_db, QColor(180, 30, 30), f"A worse (>+{threshold_db:.0f} dB)"
                ),
                QgsColorRampShader.ColorRampItem(
                    1e6, QColor(180, 30, 30), f"A worse (>+{threshold_db:.0f} dB)"
                ),
            ]
        else:
            entries = [
                QgsColorRampShader.ColorRampItem(
                    -threshold_db * 2, QColor(30, 80, 180, 200), f"A better (<-{threshold_db:.0f} dB)"
                ),
                QgsColorRampShader.ColorRampItem(
                    -threshold_db, QColor(80, 150, 220, 210), f"-{threshold_db:.0f} dB"
                ),
                QgsColorRampShader.ColorRampItem(
                    0.0, QColor(255, 255, 255, 255), "No change"
                ),
                QgsColorRampShader.ColorRampItem(
                    threshold_db, QColor(220, 150, 80, 210), f"+{threshold_db:.0f} dB"
                ),
                QgsColorRampShader.ColorRampItem(
                    threshold_db * 2, QColor(180, 30, 30, 200), f"A worse (>+{threshold_db:.0f} dB)"
                ),
            ]

        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
        color_ramp_shader.setColorRampItemList(entries)

        shader = QgsRasterShader()
        shader.setRasterShaderFunction(color_ramp_shader)

        renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def _write_html_report(self, path, panel_a_info, panel_b_info, delta_info):
        """Write an HTML comparison report."""
        import html

        panel_a = panel_a_info
        panel_b = panel_b_info
        delta = delta_info

        rows = []
        for panel, label in [(panel_a, "Panel A"), (panel_b, "Panel B")]:
            rows.append(f"<h3>{label}</h3>")
            rows.append("<table>")
            rows.append(f"<tr><th>TX Location</th><td>{panel['tx_lat']:.5f}, {panel['tx_lon']:.5f}</td></tr>")
            rows.append(f"<tr><th>TX Height</th><td>{panel['tx_h']:.1f} m</td></tr>")
            rows.append(f"<tr><th>RX Height</th><td>{panel['rx_h']:.1f} m</td></tr>")
            rows.append(f"<tr><th>Frequency</th><td>{panel['f_mhz']:.1f} MHz</td></tr>")
            rows.append(f"<tr><th>Radius</th><td>{panel['radius_km']:.1f} km</td></tr>")
            rows.append(f"<tr><th>TX Power</th><td>{panel['tx_power']:.1f} dBm</td></tr>")
            rows.append(f"<tr><th>TX Gain</th><td>{panel['tx_gain']:.1f} dBi</td></tr>")
            rows.append(f"<tr><th>RX Gain</th><td>{panel['rx_gain']:.1f} dBi</td></tr>")
            rows.append(f"<tr><th>Cable Loss</th><td>{panel['cable_loss']:.1f} dB</td></tr>")
            rows.append(f"<tr><th>Valid Pixels</th><td>{panel['valid_pixels']} / {panel['total_pixels']}</td></tr>")
            rows.append(f"<tr><th>Mean Received Power</th><td>{panel['mean_prx']:.1f} dBm</td></tr>")
            rows.append("</table>")

        delta_rows = f"""
        <h3>Delta Summary (A - B)</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><th>Delta Style</th><td>{html.escape(delta['style'])}</td></tr>
            <tr><th>Threshold</th><td>{delta['threshold_db']:.1f} dB</td></tr>
            <tr><th>Valid Delta Pixels</th><td>{delta['valid_pixels']}</td></tr>
            <tr><th>Improved (A better than B)</th><td>{delta['improved_pixels']} ({delta['improved_pct']:.1f}%)</td></tr>
            <tr><th>Degraded (A worse than B)</th><td>{delta['degraded_pixels']} ({delta['degraded_pct']:.1f}%)</td></tr>
            <tr><th>Unchanged</th><td>{delta['unchanged_pixels']} ({delta['unchanged_pct']:.1f}%)</td></tr>
            <tr><th>Min Delta</th><td>{delta['min_delta']:.2f} dB</td></tr>
            <tr><th>Max Delta</th><td>{delta['max_delta']:.2f} dB</td></tr>
            <tr><th>Mean Delta</th><td>{delta['mean_delta']:.2f} dB</td></tr>
        </table>
        """

        document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>NoWires Coverage Comparison Report</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; }}
      h1, h2, h3 {{ margin: 0 0 12px; }}
      section {{ margin: 0 0 20px; }}
      table {{ border-collapse: collapse; width: 100%; max-width: 960px; margin-bottom: 16px; }}
      th, td {{ border: 1px solid #cbd2d9; padding: 8px 10px; text-align: left; }}
      th {{ background: #f5f7fa; width: 32%; }}
      .delta-summary {{ margin: 0 0 20px; padding: 12px; background: #f5f7fa; }}
    </style>
  </head>
  <body>
    <h1>NoWires Coverage Comparison Report</h1>
    <div class="delta-summary">
      <strong>Delta Interpretation:</strong> Positive values indicate Panel A has higher path loss than Panel B (Panel B is better).
      Negative values indicate Panel A has lower path loss than Panel B (Panel A is better).
    </div>
    {''.join(rows)}
    {delta_rows}
  </body>
</html>
"""
        path.write_text(document, encoding="utf-8")

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
        panel_a = self._run_panel_coverage(
            "PANEL_A", parameters, context, feedback, elev, south, north, west, east
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
        panel_b = self._run_panel_coverage(
            "PANEL_B", parameters, context, feedback, elev, south, north, west, east
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

        loss_delta_grid = loss_grid_a - loss_grid_b
        valid_mask = ~np.isnan(loss_grid_a) & ~np.isnan(loss_grid_b)

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

        self._write_coverage_raster(output_a_path, prx_grid_a, min_lat_a, max_lat_a, min_lon_a, max_lon_a, panel_a["rx_sens"])
        self._write_coverage_raster(output_b_path, prx_grid_b, min_lat_b, max_lat_b, min_lon_b, max_lon_b, panel_b["rx_sens"])

        driver = gdal.GetDriverByName("GTiff")
        n_rows, n_cols = loss_delta_grid.shape
        ds_delta = driver.Create(output_delta_path, n_cols, n_rows, 1, gdal.GDT_Float32)
        if ds_delta is None:
            raise QgsProcessingException("Failed to create GeoTIFF: {}".format(output_delta_path))
        try:
            ds_delta.SetGeoTransform(
                [
                    min_lon_a,
                    (max_lon_a - min_lon_a) / n_cols,
                    0,
                    max_lat_a,
                    0,
                    -(max_lat_a - min_lat_a) / n_rows,
                ]
            )
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            ds_delta.SetProjection(srs.ExportToWkt())
            band_delta = ds_delta.GetRasterBand(1)
            band_delta.SetNoDataValue(-9999.0)
            band_delta.WriteArray(grid_to_raster_array(loss_delta_grid))
            band_delta.FlushCache()
        finally:
            ds_delta = None

        layer_delta = QgsRasterLayer(output_delta_path, "Coverage Delta (A - B dB)")
        if layer_delta.isValid():
            self._apply_delta_style(layer_delta, threshold_db, style=delta_style)
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

        valid_delta = valid_mask & ~np.isnan(loss_delta_grid)
        valid_count = int(valid_delta.sum())
        total_count = int(valid_mask.sum())

        if valid_count > 0:
            delta_values = loss_delta_grid[valid_delta]
            improved = int((delta_values < -threshold_db).sum())
            degraded = int((delta_values > threshold_db).sum())
            unchanged = valid_count - improved - degraded
            min_delta = float(np.nanmin(delta_values))
            max_delta = float(np.nanmax(delta_values))
            mean_delta = float(np.nanmean(delta_values))
        else:
            improved = degraded = unchanged = 0
            min_delta = max_delta = mean_delta = 0.0

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
                self._write_html_report(Path(output_report_path), panel_a_info, panel_b_info, delta_info)
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
