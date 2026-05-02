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
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
)
from .radio import (
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MIN_TERMINAL_HEIGHT_M,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_N0,
    ITM_MAX_N0,
    ITM_MIN_SIGMA,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .clutter import CLUTTER_MODEL_OPTIONS, CLUTTER_OVERRIDE_OPTIONS

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

BATCH_PARAM_CONSTANTS = {
    "MODE": MODE,
    "TX_POINT": TX_POINT,
    "RX_LAYER": RX_LAYER,
    "RX_POINT": RX_POINT,
    "TX_LAYER": TX_LAYER,
    "TX_HEIGHT": TX_HEIGHT,
    "RX_HEIGHT": RX_HEIGHT,
    "FREQ_MHZ": FREQ_MHZ,
    "POLARIZATION": POLARIZATION,
    "CLIMATE": CLIMATE,
    "TIME_PCT": TIME_PCT,
    "LOCATION_PCT": LOCATION_PCT,
    "SITUATION_PCT": SITUATION_PCT,
    "TX_POWER": TX_POWER,
    "TX_GAIN": TX_GAIN,
    "RX_GAIN": RX_GAIN,
    "CABLE_LOSS": CABLE_LOSS,
    "RX_SENSITIVITY": RX_SENSITIVITY,
    "TX_ANTENNA_PRESET": TX_ANTENNA_PRESET,
    "TX_ANTENNA_AZ": TX_ANTENNA_AZ,
    "TX_FRONT_BACK_DB": TX_FRONT_BACK_DB,
    "RX_ANTENNA_PRESET": RX_ANTENNA_PRESET,
    "RX_ANTENNA_AZ": RX_ANTENNA_AZ,
    "RX_FRONT_BACK_DB": RX_FRONT_BACK_DB,
    "CLUTTER_MODEL": CLUTTER_MODEL,
    "CLUTTER_RASTER": CLUTTER_RASTER,
    "TX_CLUTTER_OVERRIDE": TX_CLUTTER_OVERRIDE,
    "RX_CLUTTER_OVERRIDE": RX_CLUTTER_OVERRIDE,
    "K_FACTOR_PRESET": K_FACTOR_PRESET,
    "K_FACTOR": K_FACTOR,
    "N0": N0,
    "EPSILON": EPSILON,
    "SIGMA": SIGMA,
    "RANK_BY": RANK_BY,
    "OUTPUT_MARKERS": OUTPUT_MARKERS,
    "OUTPUT_CSV": OUTPUT_CSV,
    "OUTPUT_JSON": OUTPUT_JSON,
}


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
        type=QgsProcessingParameterNumber.Double, defaultValue=30.0,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    algorithm.addParameter(QgsProcessingParameterNumber(
        RX_HEIGHT, "RX antenna height (m)",
        type=QgsProcessingParameterNumber.Double, defaultValue=10.0,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    algorithm.addParameter(QgsProcessingParameterNumber(
        FREQ_MHZ, "Frequency (MHz)",
        type=QgsProcessingParameterNumber.Double, defaultValue=300.0,
        minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        POLARIZATION, "Polarization",
        options=["Horizontal", "Vertical"], defaultValue=1))
    algorithm.addParameter(QgsProcessingParameterEnum(
        CLIMATE, "Climate zone", options=[
            "Equatorial", "Continental Subtropical", "Maritime Subtropical",
            "Desert", "Continental Temperate", "Maritime Temperate (land)",
            "Maritime Temperate (sea)"], defaultValue=1))
    algorithm.addParameter(QgsProcessingParameterNumber(
        TIME_PCT, "Time percentage",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=50.0, minValue=0.01, maxValue=99.99))
    algorithm.addParameter(QgsProcessingParameterNumber(
        LOCATION_PCT, "Location percentage",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=50.0, minValue=0.01, maxValue=99.99))
    algorithm.addParameter(QgsProcessingParameterNumber(
        SITUATION_PCT, "Situation percentage",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=50.0, minValue=0.01, maxValue=99.99))


def _add_budget_params(algorithm):
    algorithm.addParameter(QgsProcessingParameterNumber(
        TX_POWER, "TX power (dBm)",
        type=QgsProcessingParameterNumber.Double, defaultValue=43.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        TX_GAIN, "TX antenna gain (dBi)",
        type=QgsProcessingParameterNumber.Double, defaultValue=8.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        RX_GAIN, "RX antenna gain (dBi)",
        type=QgsProcessingParameterNumber.Double, defaultValue=2.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        CABLE_LOSS, "Cable loss (dB)",
        type=QgsProcessingParameterNumber.Double, defaultValue=2.0, minValue=0.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        RX_SENSITIVITY, "RX sensitivity (dBm)",
        type=QgsProcessingParameterNumber.Double, defaultValue=-100.0))


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
        defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True))
    algorithm.addParameter(QgsProcessingParameterNumber(
        getattr(algorithm, prefix + "FRONT_BACK_DB"),
        label + " front-to-back ratio (dB)",
        type=QgsProcessingParameterNumber.Double, defaultValue=25.0, minValue=0.0))


def _add_clutter_params(algorithm):
    algorithm.addParameter(QgsProcessingParameterEnum(
        CLUTTER_MODEL, "Clutter correction",
        options=CLUTTER_MODEL_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterFile(
        CLUTTER_RASTER, "Land-cover raster (auto-downloaded if blank)",
        extension="tif", optional=True))
    algorithm.addParameter(QgsProcessingParameterEnum(
        TX_CLUTTER_OVERRIDE, "TX clutter override",
        options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterEnum(
        RX_CLUTTER_OVERRIDE, "RX clutter override",
        options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0))


def _add_advanced_params(algorithm):
    def _adv(p):
        p.setFlags(p.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        return p
    algorithm.addParameter(QgsProcessingParameterEnum(
        K_FACTOR_PRESET, "Earth radius factor preset (k)", options=[
            "0.67 - Sub-refractive", "1.00 - Geometric",
            "1.33 - Standard atmosphere", "2.00 - Super-refractive",
            "4.00 - Strong super-refractive", "Custom"], defaultValue=2))
    algorithm.addParameter(_adv(QgsProcessingParameterNumber(
        K_FACTOR, "Custom Earth radius factor (k)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=4.0 / 3.0, minValue=0.1)))
    algorithm.addParameter(_adv(QgsProcessingParameterNumber(
        N0, "Surface refractivity N0 (N-units)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=301.0, minValue=ITM_MIN_N0, maxValue=ITM_MAX_N0)))
    algorithm.addParameter(_adv(QgsProcessingParameterNumber(
        EPSILON, "Earth permittivity (epsilon)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=15.0, minValue=1.0)))
    algorithm.addParameter(_adv(QgsProcessingParameterNumber(
        SIGMA, "Earth conductivity (sigma, S/m)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=0.005, minValue=ITM_MIN_SIGMA)))


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
    _add_budget_params(algorithm)
    _add_antenna_params(algorithm, "TX_")
    _add_antenna_params(algorithm, "RX_")
    _add_clutter_params(algorithm)
    _add_advanced_params(algorithm)
    _add_output_params(algorithm)