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


Batch P2P parameter definitions and constants.
"""

from qgis.core import (
    Qgis,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
)
from .defaults import (
    DEFAULT_ANTENNA_AZIMUTH,
    DEFAULT_FREQ_MHZ,
    DEFAULT_FRONT_BACK_DB,
    DEFAULT_RX_HEIGHT_M,
    DEFAULT_TIME_PCT,
    DEFAULT_TX_HEIGHT_M,
)
from .radio import (
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MIN_TERMINAL_HEIGHT_M,
    ITM_MAX_TERMINAL_HEIGHT_M,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .constants import CLIMATE_OPTIONS
from .shared_params import add_link_budget_params, add_clutter_params, add_advanced_itm_params

__all__ = [
    "MODE", "TX_POINT", "RX_LAYER", "RX_POINT", "TX_LAYER",
    "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "POLARIZATION", "CLIMATE",
    "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT", "TX_POWER", "TX_GAIN",
    "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY", "TX_ANTENNA_PRESET",
    "TX_ANTENNA_AZ", "TX_FRONT_BACK_DB", "RX_ANTENNA_PRESET",
    "RX_ANTENNA_AZ", "RX_FRONT_BACK_DB", "CLUTTER_MODEL",
    "CLUTTER_RASTER", "TX_CLUTTER_OVERRIDE", "RX_CLUTTER_OVERRIDE",
    "K_FACTOR_PRESET", "K_FACTOR", "N0", "EPSILON", "SIGMA", "RANK_BY",
    "OUTPUT_MARKERS", "OUTPUT_CSV", "OUTPUT_JSON",
    "BATCH_MODE_OPTIONS", "RANK_BY_OPTIONS",
    "BATCH_PARAM_CONSTANTS",
    "add_batch_params",
]

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

BATCH_MODE_OPTIONS = ["One-to-Many (single TX → multiple RX)", "Many-to-One (multiple TX → single RX)"]
RANK_BY_OPTIONS = ["Link margin (descending)", "Path loss (ascending)", "Clearance (descending)"]
_BATCH_PARAM_NAMES = (
    "MODE", "TX_POINT", "RX_LAYER", "RX_POINT", "TX_LAYER",
    "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "POLARIZATION", "CLIMATE",
    "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT", "TX_POWER", "TX_GAIN",
    "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY", "TX_ANTENNA_PRESET",
    "TX_ANTENNA_AZ", "TX_FRONT_BACK_DB", "RX_ANTENNA_PRESET",
    "RX_ANTENNA_AZ", "RX_FRONT_BACK_DB", "CLUTTER_MODEL",
    "CLUTTER_RASTER", "TX_CLUTTER_OVERRIDE", "RX_CLUTTER_OVERRIDE",
    "K_FACTOR_PRESET", "K_FACTOR", "N0", "EPSILON", "SIGMA",
    "RANK_BY", "OUTPUT_MARKERS", "OUTPUT_CSV", "OUTPUT_JSON",
)
BATCH_PARAM_CONSTANTS = {k: k for k in _BATCH_PARAM_NAMES}


def _add_mode_params(algorithm):
    algorithm.addParameter(QgsProcessingParameterEnum(
        MODE, "Analysis mode", options=BATCH_MODE_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterPoint(
        TX_POINT, "TX point (for One-to-Many)", optional=True))
    algorithm.addParameter(QgsProcessingParameterFeatureSource(
        RX_LAYER, "RX point layer (for One-to-Many)",
        [Qgis.GeometryType.Point], optional=True))
    algorithm.addParameter(QgsProcessingParameterPoint(
        RX_POINT, "RX point (for Many-to-One)", optional=True))
    algorithm.addParameter(QgsProcessingParameterFeatureSource(
        TX_LAYER, "TX candidate layer (for Many-to-One)",
        [Qgis.GeometryType.Point], optional=True))


def _add_link_params(algorithm):
    algorithm.addParameter(QgsProcessingParameterNumber(
        TX_HEIGHT, "TX antenna height (m)",
        type=QgsProcessingParameterNumber.Double, defaultValue=DEFAULT_TX_HEIGHT_M,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    algorithm.addParameter(QgsProcessingParameterNumber(
        RX_HEIGHT, "RX antenna height (m)",
        type=QgsProcessingParameterNumber.Double, defaultValue=DEFAULT_RX_HEIGHT_M,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    algorithm.addParameter(QgsProcessingParameterNumber(
        FREQ_MHZ, "Frequency (MHz)",
        type=QgsProcessingParameterNumber.Double, defaultValue=DEFAULT_FREQ_MHZ,
        minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        POLARIZATION, "Polarization",
        options=["Horizontal", "Vertical"], defaultValue=1))
    algorithm.addParameter(QgsProcessingParameterEnum(
        CLIMATE, "Climate zone", options=CLIMATE_OPTIONS, defaultValue=1))
    algorithm.addParameter(QgsProcessingParameterNumber(
        TIME_PCT, "Time percentage",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=DEFAULT_TIME_PCT, minValue=0.01, maxValue=99.99))
    algorithm.addParameter(QgsProcessingParameterNumber(
        LOCATION_PCT, "Location percentage",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=DEFAULT_TIME_PCT, minValue=0.01, maxValue=99.99))
    algorithm.addParameter(QgsProcessingParameterNumber(
        SITUATION_PCT, "Situation percentage",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=DEFAULT_TIME_PCT, minValue=0.01, maxValue=99.99))


def _add_antenna_params(algorithm, prefix):
    label = prefix.rstrip("_")
    algorithm.addParameter(QgsProcessingParameterEnum(
        getattr(algorithm, prefix + "ANTENNA_PRESET"),
        label + " antenna preset",
        options=ANTENNA_PRESET_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        getattr(algorithm, prefix + "ANTENNA_AZ"),
        label + " antenna azimuth (deg)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=DEFAULT_ANTENNA_AZIMUTH, minValue=0.0, maxValue=360.0, optional=True))
    algorithm.addParameter(QgsProcessingParameterNumber(
        getattr(algorithm, prefix + "FRONT_BACK_DB"),
        label + " front-to-back ratio (dB)",
        type=QgsProcessingParameterNumber.Double, defaultValue=DEFAULT_FRONT_BACK_DB, minValue=0.0))


def _add_output_params(algorithm):
    algorithm.addParameter(QgsProcessingParameterEnum(
        RANK_BY, "Rank results by", options=RANK_BY_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        OUTPUT_MARKERS, "Ranked marker layer output",
        "GeoPackage files (*.gpkg)"))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        OUTPUT_CSV, "Batch results CSV",
        "CSV files (*.csv)", optional=True))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        OUTPUT_JSON, "Batch results JSON",
        "JSON files (*.json)", optional=True))


def add_batch_params(algorithm):
    _add_mode_params(algorithm)
    _add_link_params(algorithm)
    add_link_budget_params(algorithm)
    _add_antenna_params(algorithm, "TX_")
    _add_antenna_params(algorithm, "RX_")
    add_clutter_params(algorithm)
    add_advanced_itm_params(algorithm)
    _add_output_params(algorithm)
