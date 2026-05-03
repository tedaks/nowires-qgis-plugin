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

Parameter definitions for the Point-to-Point radio link analysis algorithm.
"""

from qgis.core import (
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
)
from .radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_TERMINAL_HEIGHT_M,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .constants import POLARIZATION_NAMES, CLIMATE_OPTIONS, K_FACTOR_PRESETS_OPTIONS
from .shared_params import add_link_budget_params, add_clutter_params, add_advanced_itm_params
from .p2p_report_display import report_p2p_results

__all__ = [
    "PARAM_CONSTANTS",
    "POLARIZATION_NAMES",
    "K_FACTOR_PRESETS_OPTIONS",
    "add_p2p_params",
    "_install_constants",
    "report_p2p_results",
]

_PARAM_NAMES = (
    "TX_POINT", "RX_POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "POLARIZATION",
    "CLIMATE", "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT", "TX_POWER", "TX_GAIN",
    "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY", "TX_ANTENNA_PRESET", "TX_ANTENNA_AZ",
    "TX_FRONT_BACK_DB", "TX_DOWNTILT_DEG", "TX_H_PATTERN", "TX_V_PATTERN",
    "RX_ANTENNA_PRESET", "RX_ANTENNA_AZ", "RX_FRONT_BACK_DB", "RX_DOWNTILT_DEG",
    "RX_H_PATTERN", "RX_V_PATTERN", "CLUTTER_MODEL", "CLUTTER_RASTER",
    "TX_CLUTTER_OVERRIDE", "RX_CLUTTER_OVERRIDE", "K_FACTOR_PRESET", "K_FACTOR",
    "N0", "EPSILON", "SIGMA", "OUTPUT_PROFILE", "OUTPUT_FRESNEL", "OUTPUT_MARKERS",
    "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON", "OUTPUT_REPORT_HTML", "SHOW_CHART",
)
PARAM_CONSTANTS = {k: k for k in _PARAM_NAMES}

_DBL = QgsProcessingParameterNumber.Double


def _install_constants(cls, constants_dict):
    for key, value in constants_dict.items():
        setattr(cls, key, value)


def _add_basic_link_params(algorithm):
    algorithm.addParameter(
        QgsProcessingParameterPoint(algorithm.TX_POINT, "Transmitter (TX) point"))
    algorithm.addParameter(
        QgsProcessingParameterPoint(algorithm.RX_POINT, "Receiver (RX) point"))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.TX_HEIGHT, "TX antenna height (m)", type=_DBL,
        defaultValue=30.0, minValue=ITM_MIN_TERMINAL_HEIGHT_M,
        maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.RX_HEIGHT, "RX antenna height (m)", type=_DBL,
        defaultValue=10.0, minValue=ITM_MIN_TERMINAL_HEIGHT_M,
        maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.FREQ_MHZ, "Frequency (MHz)", type=_DBL, defaultValue=300.0,
        minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.POLARIZATION, "Polarization",
        options=["Horizontal", "Vertical"], defaultValue=1))
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.CLIMATE, "Climate zone",
        options=CLIMATE_OPTIONS, defaultValue=1))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.TIME_PCT, "Time percentage", type=_DBL,
        defaultValue=50.0, minValue=0.01, maxValue=99.99))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.LOCATION_PCT, "Location percentage", type=_DBL,
        defaultValue=50.0, minValue=0.01, maxValue=99.99))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.SITUATION_PCT, "Situation percentage", type=_DBL,
        defaultValue=50.0, minValue=0.01, maxValue=99.99))


def _add_antenna_params(algorithm, prefix):
    label = "TX" if prefix == "TX_" else "RX"
    algorithm.addParameter(QgsProcessingParameterEnum(
        getattr(algorithm, prefix + "ANTENNA_PRESET"), "{} antenna preset".format(label),
        options=ANTENNA_PRESET_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        getattr(algorithm, prefix + "ANTENNA_AZ"), "{} antenna azimuth (deg)".format(label),
        type=_DBL, defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True))
    algorithm.addParameter(QgsProcessingParameterNumber(
        getattr(algorithm, prefix + "FRONT_BACK_DB"),
        "{} front-to-back ratio (dB)".format(label),
        type=_DBL, defaultValue=25.0, minValue=0.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        getattr(algorithm, prefix + "DOWNTILT_DEG"), "{} downtilt (deg)".format(label),
        type=_DBL, defaultValue=0.0, minValue=-45.0, maxValue=45.0))
    algorithm.addParameter(QgsProcessingParameterFile(
        getattr(algorithm, prefix + "H_PATTERN"), "{} horizontal pattern CSV".format(label),
        extension="csv", optional=True))
    algorithm.addParameter(QgsProcessingParameterFile(
        getattr(algorithm, prefix + "V_PATTERN"), "{} vertical pattern CSV".format(label),
        extension="csv", optional=True))


def _add_output_params(algorithm):
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        algorithm.OUTPUT_PROFILE, "Profile line output",
        "GeoPackage files (*.gpkg)"))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        algorithm.OUTPUT_FRESNEL, "Fresnel zone polygon",
        "GeoPackage files (*.gpkg)"))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        algorithm.OUTPUT_MARKERS, "TX/RX marker output",
        "GeoPackage files (*.gpkg)"))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        algorithm.OUTPUT_REPORT_CSV, "P2P report CSV",
        "CSV files (*.csv)", optional=True))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        algorithm.OUTPUT_REPORT_JSON, "P2P report JSON",
        "JSON files (*.json)", optional=True))
    algorithm.addParameter(QgsProcessingParameterFileDestination(
        algorithm.OUTPUT_REPORT_HTML, "P2P report HTML",
        "HTML files (*.html)", optional=True))
    algorithm.addParameter(QgsProcessingParameterBoolean(
        algorithm.SHOW_CHART, "Show profile chart after analysis",
        defaultValue=True, optional=False))


def add_p2p_params(algorithm):
    _add_basic_link_params(algorithm)
    add_link_budget_params(algorithm)
    _add_antenna_params(algorithm, "TX_")
    _add_antenna_params(algorithm, "RX_")
    add_clutter_params(algorithm)
    add_advanced_itm_params(algorithm)
    _add_output_params(algorithm)