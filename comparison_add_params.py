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


Coverage Comparison Algorithm — Parameter registration helpers.

Functions that register QGIS processing parameters for the comparison
algorithm's two panels and shared outputs.
"""

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
)

from .antenna import ANTENNA_PRESET_OPTIONS
from .comparison_params import (
    DELTA_STYLE_OPTIONS,
    OUTPUT_CONSTANTS,
)
from .constants import CLIMATE_OPTIONS, GRID_SIZE_OPTIONS
from .defaults import (
    DEFAULT_ANTENNA_AZIMUTH,
    DEFAULT_ANTENNA_BEAMWIDTH,
    DEFAULT_CABLE_LOSS_DB,
    DEFAULT_DOWNTILT_DEG,
    DEFAULT_EPSILON,
    DEFAULT_FREQ_MHZ,
    DEFAULT_FRONT_BACK_DB,
    DEFAULT_LOCATION_PCT,
    DEFAULT_N0,
    DEFAULT_RADIUS_KM,
    DEFAULT_RX_GAIN_DBI,
    DEFAULT_RX_HEIGHT_M,
    DEFAULT_RX_SENSITIVITY_DBM,
    DEFAULT_SIGMA,
    DEFAULT_SITUATION_PCT,
    DEFAULT_TIME_PCT,
    DEFAULT_TX_GAIN_DBI,
    DEFAULT_TX_HEIGHT_M,
    DEFAULT_TX_POWER_DBM,
)
from .shared_params import add_clutter_params

__all__ = ["add_panel_params", "add_comparison_params"]


def add_panel_params(algorithm, prefix, config):
    panel_label = prefix.split("_")[1]
    algorithm.addParameter(
        config["point_param"](f"{prefix}_POINT", f"Panel {panel_label} Transmitter (TX) point")
    )
    algorithm.addParameter(
        config["height_param"](
            f"{prefix}_TX_HEIGHT", f"Panel {panel_label} TX antenna height (m)", defaultValue=DEFAULT_TX_HEIGHT_M,
        )
    )
    algorithm.addParameter(
        config["height_param"](
            f"{prefix}_RX_HEIGHT", f"Panel {panel_label} RX antenna height (m)", defaultValue=DEFAULT_RX_HEIGHT_M,
        )
    )
    algorithm.addParameter(
        config["freq_param"](
            f"{prefix}_FREQ_MHZ", f"Panel {panel_label} Frequency (MHz)", defaultValue=DEFAULT_FREQ_MHZ,
        )
    )
    algorithm.addParameter(
        config["radius_param"](
            f"{prefix}_RADIUS_KM", f"Panel {panel_label} Max analysis distance (km)", defaultValue=DEFAULT_RADIUS_KM,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            f"{prefix}_GRID_SIZE", f"Panel {panel_label} Grid size resolution",
            options=GRID_SIZE_OPTIONS,
            defaultValue=2,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            f"{prefix}_POLARIZATION", f"Panel {panel_label} Polarization",
            options=["Horizontal", "Vertical"], defaultValue=1,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            f"{prefix}_CLIMATE", f"Panel {panel_label} Climate zone",
            options=CLIMATE_OPTIONS,
            defaultValue=1,
        )
    )
    algorithm.addParameter(
        config["pct_param"](
            f"{prefix}_TIME_PCT", f"Panel {panel_label} Time percentage", defaultValue=DEFAULT_TIME_PCT,
        )
    )
    algorithm.addParameter(
        config["pct_param"](
            f"{prefix}_LOCATION_PCT", f"Panel {panel_label} Location percentage", defaultValue=DEFAULT_LOCATION_PCT,
        )
    )
    algorithm.addParameter(
        config["pct_param"](
            f"{prefix}_SITUATION_PCT", f"Panel {panel_label} Situation percentage", defaultValue=DEFAULT_SITUATION_PCT,
        )
    )
    algorithm.addParameter(
        config["dbm_param"](
            f"{prefix}_TX_POWER", f"Panel {panel_label} TX power (dBm)", defaultValue=DEFAULT_TX_POWER_DBM,
        )
    )
    algorithm.addParameter(
        config["gain_param"](
            f"{prefix}_TX_GAIN", f"Panel {panel_label} TX antenna gain (dBi)", defaultValue=DEFAULT_TX_GAIN_DBI,
        )
    )
    algorithm.addParameter(
        config["gain_param"](
            f"{prefix}_RX_GAIN", f"Panel {panel_label} RX antenna gain (dBi)", defaultValue=DEFAULT_RX_GAIN_DBI,
        )
    )
    algorithm.addParameter(
        config["loss_param"](
            f"{prefix}_CABLE_LOSS", f"Panel {panel_label} Cable loss (dB)", defaultValue=DEFAULT_CABLE_LOSS_DB,
        )
    )
    algorithm.addParameter(
        config["dbm_param"](
            f"{prefix}_RX_SENSITIVITY", f"Panel {panel_label} RX sensitivity (dBm)", defaultValue=DEFAULT_RX_SENSITIVITY_DBM,
        )
    )
    algorithm.addParameter(
        config["az_param"](
            f"{prefix}_ANTENNA_AZ", f"Panel {panel_label} Antenna azimuth (deg, blank=omni)",
            defaultValue=DEFAULT_ANTENNA_AZIMUTH, optional=True,
        )
    )
    algorithm.addParameter(
        config["bw_param"](
            f"{prefix}_ANTENNA_BW", f"Panel {panel_label} Antenna beamwidth (deg)", defaultValue=DEFAULT_ANTENNA_BEAMWIDTH,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            f"{prefix}_ANTENNA_PRESET", f"Panel {panel_label} TX antenna preset",
            options=ANTENNA_PRESET_OPTIONS, defaultValue=0,
        )
    )
    algorithm.addParameter(
        config["db_param"](
            f"{prefix}_FRONT_BACK_DB", f"Panel {panel_label} TX front-to-back ratio (dB)", defaultValue=DEFAULT_FRONT_BACK_DB,
        )
    )
    algorithm.addParameter(
        config["downtilt_param"](
            f"{prefix}_DOWNTILT_DEG", f"Panel {panel_label} TX downtilt (deg)", defaultValue=DEFAULT_DOWNTILT_DEG,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFile(
            f"{prefix}_H_PATTERN", f"Panel {panel_label} TX horizontal pattern CSV",
            extension="csv", optional=True,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFile(
            f"{prefix}_V_PATTERN", f"Panel {panel_label} TX vertical pattern CSV",
            extension="csv", optional=True,
        )
    )
    add_clutter_params(algorithm, attr_getter=lambda name: getattr(algorithm, f"{prefix}_{name}"))
    n0_param = config["n0_param"](
        f"{prefix}_N0", f"Panel {panel_label} Surface refractivity N0 (N-units)", defaultValue=DEFAULT_N0,
    )
    n0_param.setFlags(n0_param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
    algorithm.addParameter(n0_param)

    epsilon_param = config["epsilon_param"](
        f"{prefix}_EPSILON", f"Panel {panel_label} Earth permittivity (epsilon)", defaultValue=DEFAULT_EPSILON,
    )
    epsilon_param.setFlags(epsilon_param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
    algorithm.addParameter(epsilon_param)

    sigma_param = config["sigma_param"](
        f"{prefix}_SIGMA", f"Panel {panel_label} Earth conductivity (sigma, S/m)", defaultValue=DEFAULT_SIGMA,
    )
    sigma_param.setFlags(sigma_param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
    algorithm.addParameter(sigma_param)


def add_comparison_params(algorithm):
    algorithm.addParameter(
        QgsProcessingParameterFolderDestination(
            OUTPUT_CONSTANTS["OUTPUT_DIR"],
            "Output directory for coverage comparison files",
            optional=True,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            OUTPUT_CONSTANTS["DELTA_STYLE"],
            "Delta raster styling",
            options=DELTA_STYLE_OPTIONS,
            defaultValue=0,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            OUTPUT_CONSTANTS["DELTA_THRESHOLD_DB"],
            "Significant difference threshold (dB)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=5.0,
            minValue=0.1,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            OUTPUT_CONSTANTS["OUTPUT_A"],
            "Panel A coverage raster output",
            fileFilter="GeoTIFF files (*.tif)",
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            OUTPUT_CONSTANTS["OUTPUT_B"],
            "Panel B coverage raster output",
            fileFilter="GeoTIFF files (*.tif)",
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            OUTPUT_CONSTANTS["OUTPUT_DELTA"],
            "Delta raster output (A - B in dB)",
            fileFilter="GeoTIFF files (*.tif)",
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            OUTPUT_CONSTANTS["OUTPUT_REPORT_HTML"],
            "Comparison report HTML",
            fileFilter="HTML files (*.html)",
            optional=True,
        )
    )