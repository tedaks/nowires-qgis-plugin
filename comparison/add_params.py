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
    QgsProcessingParameterRasterDestination,
)

from NoWires.antenna import ANTENNA_PRESET_OPTIONS
from NoWires.comparison.params import (
    DELTA_STYLE_OPTIONS,
    OUTPUT_CONSTANTS,
)
from NoWires.constants import CLIMATE_OPTIONS, GRID_SIZE_OPTIONS
from NoWires.defaults import (
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
from NoWires.shared_params import add_clutter_params

__all__ = ["add_panel_params", "add_comparison_params"]


def _add_panel_advanced_params(algorithm, prefix, config, panel_label):
    """Add N0, epsilon, and sigma advanced parameters for a comparison panel."""
    specs = [
        ("n0_param", "N0", "Surface refractivity N0 (N-units)", DEFAULT_N0),
        ("epsilon_param", "EPSILON", "Earth permittivity (epsilon)", DEFAULT_EPSILON),
        ("sigma_param", "SIGMA", "Earth conductivity (sigma, S/m)", DEFAULT_SIGMA),
    ]
    for ckey, pname, desc, default in specs:
        param = config[ckey](
            f"{prefix}_{pname}",
            f"Panel {panel_label} {desc}",
            defaultValue=default,
        )
        param.setFlags(param.flags() | QgsProcessingParameterNumber.Flag.FlagAdvanced)
        algorithm.addParameter(param)


def add_panel_params(algorithm, prefix, config):
    parts = prefix.split("_")
    panel_label = parts[1] if len(parts) > 1 else prefix
    algorithm.addParameter(
        config["point_param"](f"{prefix}_POINT", f"Panel {panel_label} Transmitter (TX) point")
    )
    algorithm.addParameter(
        config["height_param"](
            f"{prefix}_TX_HEIGHT",
            f"Panel {panel_label} TX antenna height (m)",
            defaultValue=DEFAULT_TX_HEIGHT_M,
        )
    )
    algorithm.addParameter(
        config["height_param"](
            f"{prefix}_RX_HEIGHT",
            f"Panel {panel_label} RX antenna height (m)",
            defaultValue=DEFAULT_RX_HEIGHT_M,
        )
    )
    algorithm.addParameter(
        config["freq_param"](
            f"{prefix}_FREQ_MHZ",
            f"Panel {panel_label} Frequency (MHz)",
            defaultValue=DEFAULT_FREQ_MHZ,
        )
    )
    algorithm.addParameter(
        config["radius_param"](
            f"{prefix}_RADIUS_KM",
            f"Panel {panel_label} Max analysis distance (km)",
            defaultValue=DEFAULT_RADIUS_KM,
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
            f"{prefix}_TIME_PCT",
            f"Panel {panel_label} Time percentage",
            defaultValue=DEFAULT_TIME_PCT,
        )
    )
    algorithm.addParameter(
        config["pct_param"](
            f"{prefix}_LOCATION_PCT",
            f"Panel {panel_label} Location percentage",
            defaultValue=DEFAULT_LOCATION_PCT,
        )
    )
    algorithm.addParameter(
        config["pct_param"](
            f"{prefix}_SITUATION_PCT",
            f"Panel {panel_label} Situation percentage",
            defaultValue=DEFAULT_SITUATION_PCT,
        )
    )
    algorithm.addParameter(
        config["dbm_param"](
            f"{prefix}_TX_POWER",
            f"Panel {panel_label} TX power (dBm)",
            defaultValue=DEFAULT_TX_POWER_DBM,
        )
    )
    algorithm.addParameter(
        config["gain_param"](
            f"{prefix}_TX_GAIN",
            f"Panel {panel_label} TX antenna gain (dBi)",
            defaultValue=DEFAULT_TX_GAIN_DBI,
        )
    )
    algorithm.addParameter(
        config["gain_param"](
            f"{prefix}_RX_GAIN",
            f"Panel {panel_label} RX antenna gain (dBi)",
            defaultValue=DEFAULT_RX_GAIN_DBI,
        )
    )
    algorithm.addParameter(
        config["loss_param"](
            f"{prefix}_CABLE_LOSS",
            f"Panel {panel_label} Cable loss (dB)",
            defaultValue=DEFAULT_CABLE_LOSS_DB,
        )
    )
    algorithm.addParameter(
        config["dbm_param"](
            f"{prefix}_RX_SENSITIVITY",
            f"Panel {panel_label} RX sensitivity (dBm)",
            defaultValue=DEFAULT_RX_SENSITIVITY_DBM,
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
            f"{prefix}_ANTENNA_BW",
            f"Panel {panel_label} Antenna beamwidth (deg)",
            defaultValue=DEFAULT_ANTENNA_BEAMWIDTH,
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
            f"{prefix}_FRONT_BACK_DB",
            f"Panel {panel_label} TX front-to-back ratio (dB)",
            defaultValue=DEFAULT_FRONT_BACK_DB,
        )
    )
    algorithm.addParameter(
        config["downtilt_param"](
            f"{prefix}_DOWNTILT_DEG",
            f"Panel {panel_label} TX downtilt (deg)",
            defaultValue=DEFAULT_DOWNTILT_DEG,
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
    add_clutter_params(algorithm, attr_getter=lambda name: f"{prefix}_{name}")
    _add_panel_advanced_params(algorithm, prefix, config, panel_label)


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
            type=QgsProcessingParameterNumber.Type.Double,
            defaultValue=5.0,
            minValue=0.1,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterRasterDestination(
            OUTPUT_CONSTANTS["OUTPUT_A"],
            "Panel A coverage raster output",
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterRasterDestination(
            OUTPUT_CONSTANTS["OUTPUT_B"],
            "Panel B coverage raster output",
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterRasterDestination(
            OUTPUT_CONSTANTS["OUTPUT_DELTA"],
            "Delta raster output (A - B in dB)",
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
