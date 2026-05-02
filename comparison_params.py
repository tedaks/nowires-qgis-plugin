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


Coverage Comparison Algorithm — Constants and config factory.

Extracted from algorithm_coverage_comparison.py for modularity.
"""

from qgis.core import QgsProcessingParameterNumber

from .constants import (
    METERS_PER_DEGREE_LAT,
    POLARIZATION_NAMES,
    GRID_SIZE_PRESETS,
)
from .radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_N0,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MIN_SIGMA,
)

__all__ = [
    "GRID_SIZE_PRESETS",
    "POLARIZATION_NAMES",
    "METERS_PER_DEGREE_LAT",
    "DELTA_STYLE_OPTIONS",
    "DELTA_THRESHOLD_DEFAULTS",
    "PANEL_A_CONSTANTS",
    "PANEL_B_CONSTANTS",
    "OUTPUT_CONSTANTS",
    "make_panel_config",
    "add_comparison_params",
]

DELTA_STYLE_OPTIONS = ["diverging", "threshold"]
DELTA_THRESHOLD_DEFAULTS = [3.0, 5.0, 10.0]

PANEL_A_CONSTANTS = {
    "POINT": "PANEL_A_POINT",
    "TX_HEIGHT": "PANEL_A_TX_HEIGHT",
    "RX_HEIGHT": "PANEL_A_RX_HEIGHT",
    "FREQ_MHZ": "PANEL_A_FREQ_MHZ",
    "RADIUS_KM": "PANEL_A_RADIUS_KM",
    "GRID_SIZE": "PANEL_A_GRID_SIZE",
    "POLARIZATION": "PANEL_A_POLARIZATION",
    "CLIMATE": "PANEL_A_CLIMATE",
    "TIME_PCT": "PANEL_A_TIME_PCT",
    "LOCATION_PCT": "PANEL_A_LOCATION_PCT",
    "SITUATION_PCT": "PANEL_A_SITUATION_PCT",
    "TX_POWER": "PANEL_A_TX_POWER",
    "TX_GAIN": "PANEL_A_TX_GAIN",
    "RX_GAIN": "PANEL_A_RX_GAIN",
    "CABLE_LOSS": "PANEL_A_CABLE_LOSS",
    "RX_SENSITIVITY": "PANEL_A_RX_SENSITIVITY",
    "ANTENNA_BW": "PANEL_A_ANTENNA_BW",
    "ANTENNA_AZ": "PANEL_A_ANTENNA_AZ",
    "ANTENNA_PRESET": "PANEL_A_ANTENNA_PRESET",
    "FRONT_BACK_DB": "PANEL_A_FRONT_BACK_DB",
    "DOWNTILT_DEG": "PANEL_A_DOWNTILT_DEG",
    "H_PATTERN": "PANEL_A_H_PATTERN",
    "V_PATTERN": "PANEL_A_V_PATTERN",
    "CLUTTER_MODEL": "PANEL_A_CLUTTER_MODEL",
    "CLUTTER_RASTER": "PANEL_A_CLUTTER_RASTER",
    "TX_CLUTTER_OVERRIDE": "PANEL_A_TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE": "PANEL_A_RX_CLUTTER_OVERRIDE",
    "N0": "PANEL_A_N0",
    "EPSILON": "PANEL_A_EPSILON",
    "SIGMA": "PANEL_A_SIGMA",
}

PANEL_B_CONSTANTS = {
    "POINT": "PANEL_B_POINT",
    "TX_HEIGHT": "PANEL_B_TX_HEIGHT",
    "RX_HEIGHT": "PANEL_B_RX_HEIGHT",
    "FREQ_MHZ": "PANEL_B_FREQ_MHZ",
    "RADIUS_KM": "PANEL_B_RADIUS_KM",
    "GRID_SIZE": "PANEL_B_GRID_SIZE",
    "POLARIZATION": "PANEL_B_POLARIZATION",
    "CLIMATE": "PANEL_B_CLIMATE",
    "TIME_PCT": "PANEL_B_TIME_PCT",
    "LOCATION_PCT": "PANEL_B_LOCATION_PCT",
    "SITUATION_PCT": "PANEL_B_SITUATION_PCT",
    "TX_POWER": "PANEL_B_TX_POWER",
    "TX_GAIN": "PANEL_B_TX_GAIN",
    "RX_GAIN": "PANEL_B_RX_GAIN",
    "CABLE_LOSS": "PANEL_B_CABLE_LOSS",
    "RX_SENSITIVITY": "PANEL_B_RX_SENSITIVITY",
    "ANTENNA_BW": "PANEL_B_ANTENNA_BW",
    "ANTENNA_AZ": "PANEL_B_ANTENNA_AZ",
    "ANTENNA_PRESET": "PANEL_B_ANTENNA_PRESET",
    "FRONT_BACK_DB": "PANEL_B_FRONT_BACK_DB",
    "DOWNTILT_DEG": "PANEL_B_DOWNTILT_DEG",
    "H_PATTERN": "PANEL_B_H_PATTERN",
    "V_PATTERN": "PANEL_B_V_PATTERN",
    "CLUTTER_MODEL": "PANEL_B_CLUTTER_MODEL",
    "CLUTTER_RASTER": "PANEL_B_CLUTTER_RASTER",
    "TX_CLUTTER_OVERRIDE": "PANEL_B_TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE": "PANEL_B_RX_CLUTTER_OVERRIDE",
    "N0": "PANEL_B_N0",
    "EPSILON": "PANEL_B_EPSILON",
    "SIGMA": "PANEL_B_SIGMA",
}

OUTPUT_CONSTANTS = {
    "OUTPUT_DIR": "OUTPUT_DIR",
    "DELTA_STYLE": "DELTA_STYLE",
    "DELTA_THRESHOLD_DB": "DELTA_THRESHOLD_DB",
    "OUTPUT_A": "OUTPUT_A",
    "OUTPUT_B": "OUTPUT_B",
    "OUTPUT_DELTA": "OUTPUT_DELTA",
    "OUTPUT_REPORT_HTML": "OUTPUT_REPORT_HTML",
}


def make_panel_config():
    return {
        "point_param": lambda name, desc: _point_param(name, desc),
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
        "gain_param": lambda name, desc, **kw: QgsProcessingParameterNumber(
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


def _point_param(name, desc):
    from qgis.core import QgsProcessingParameterPoint
    return QgsProcessingParameterPoint(name, desc)