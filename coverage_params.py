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


Coverage Algorithm — Parameter definitions and constants.

Extracted from algorithm_coverage.py for modularity.
"""

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsCoordinateReferenceSystem,
)
from .radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_N0,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MIN_SIGMA,
    ITM_MIN_TERMINAL_HEIGHT_M,
    validate_itm_input_ranges,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .clutter import (
    CLUTTER_MODEL_OPTIONS,
    CLUTTER_OVERRIDE_OPTIONS,
    LandCoverGrid,
    clutter_override_value,
)
from .constants import (
    METERS_PER_DEGREE_LAT,
    POLARIZATION_NAMES,
    CLIMATE_OPTIONS,
    GRID_SIZE_PRESETS,
    GRID_SIZE_OPTIONS,
)
from .shared_params import add_link_budget_params, add_clutter_params, add_advanced_itm_params

_PARAM_NAMES = (
    "TX_POINT", "AREA", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "RADIUS_KM",
    "GRID_SIZE", "POLARIZATION", "CLIMATE", "TIME_PCT", "LOCATION_PCT",
    "SITUATION_PCT", "TX_POWER", "TX_GAIN", "RX_GAIN", "CABLE_LOSS",
    "RX_SENSITIVITY", "ANTENNA_BW", "ANTENNA_AZ", "ANTENNA_PRESET",
    "FRONT_BACK_DB", "DOWNTILT_DEG", "H_PATTERN", "V_PATTERN",
    "CLUTTER_MODEL", "CLUTTER_RASTER", "TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE", "N0", "EPSILON", "SIGMA", "OUTPUT_RASTER",
    "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON", "OUTPUT_REPORT_HTML",
)
PARAM_CONSTANTS = {k: k for k in _PARAM_NAMES}


def _install_constants(cls, constants_dict):
    for key, value in constants_dict.items():
        setattr(cls, key, value)


_DBL = QgsProcessingParameterNumber.Double


def _add_basic_params(alg):
    alg.addParameter(QgsProcessingParameterPoint(
        alg.TX_POINT, "Transmitter (TX) point"))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.TX_HEIGHT, "TX antenna height (m)", type=_DBL, defaultValue=30.0,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.RX_HEIGHT, "RX antenna height (m)", type=_DBL, defaultValue=10.0,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.FREQ_MHZ, "Frequency (MHz)", type=_DBL, defaultValue=300.0,
        minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.RADIUS_KM, "Max analysis distance (km)", type=_DBL,
        defaultValue=50.0, minValue=1.0, maxValue=500.0))
    alg.addParameter(QgsProcessingParameterEnum(
        alg.GRID_SIZE, "Grid size resolution",
        options=GRID_SIZE_OPTIONS, defaultValue=2))
    alg.addParameter(QgsProcessingParameterEnum(
        alg.POLARIZATION, "Polarization",
        options=["Horizontal", "Vertical"], defaultValue=1))
    alg.addParameter(QgsProcessingParameterEnum(
        alg.CLIMATE, "Climate zone",
        options=CLIMATE_OPTIONS, defaultValue=1))


def _add_pct_params(alg):
    for attr, label in (
        (alg.TIME_PCT, "Time percentage"),
        (alg.LOCATION_PCT, "Location percentage"),
        (alg.SITUATION_PCT, "Situation percentage"),
    ):
        alg.addParameter(QgsProcessingParameterNumber(
            attr, label, type=_DBL, defaultValue=50.0, minValue=0.01, maxValue=99.99))


def _add_antenna_params(alg):
    alg.addParameter(QgsProcessingParameterNumber(
        alg.ANTENNA_AZ, "Antenna azimuth (deg, blank=omni)", type=_DBL,
        defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.ANTENNA_BW, "Antenna beamwidth (deg)", type=_DBL,
        defaultValue=360.0, minValue=1.0, maxValue=360.0))
    alg.addParameter(QgsProcessingParameterEnum(
        alg.ANTENNA_PRESET, "TX antenna preset",
        options=ANTENNA_PRESET_OPTIONS, defaultValue=0))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.FRONT_BACK_DB, "TX front-to-back ratio (dB)", type=_DBL,
        defaultValue=25.0, minValue=0.0))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.DOWNTILT_DEG, "TX downtilt (deg)", type=_DBL,
        defaultValue=0.0, minValue=-45.0, maxValue=45.0))
    alg.addParameter(QgsProcessingParameterFile(
        alg.H_PATTERN, "TX horizontal pattern CSV", extension="csv", optional=True))
    alg.addParameter(QgsProcessingParameterFile(
        alg.V_PATTERN, "TX vertical pattern CSV", extension="csv", optional=True))


def _add_output_params(alg):
    alg.addParameter(QgsProcessingParameterFileDestination(
        alg.OUTPUT_RASTER, "Coverage raster output", "GeoTIFF files (*.tif)"))
    alg.addParameter(QgsProcessingParameterFileDestination(
        alg.OUTPUT_REPORT_CSV, "Coverage report CSV",
        "CSV files (*.csv)", optional=True))
    alg.addParameter(QgsProcessingParameterFileDestination(
        alg.OUTPUT_REPORT_JSON, "Coverage report JSON",
        "JSON files (*.json)", optional=True))
    alg.addParameter(QgsProcessingParameterFileDestination(
        alg.OUTPUT_REPORT_HTML, "Coverage report HTML",
        "HTML files (*.html)", optional=True))


def add_coverage_params(algorithm):
    _add_basic_params(algorithm)
    _add_pct_params(algorithm)
    add_link_budget_params(algorithm)
    _add_antenna_params(algorithm)
    add_clutter_params(algorithm)
    add_advanced_itm_params(algorithm, include_k_factor=False)
    _add_output_params(algorithm)


def extract_coverage_params(alg, parameters, context):
    _dbl = alg.parameterAsDouble
    _enum = alg.parameterAsEnum
    p = {}
    tx_point = alg.parameterAsPoint(
        parameters, alg.TX_POINT, context,
        crs=QgsCoordinateReferenceSystem("EPSG:4326"),
    )
    if tx_point is None:
        raise ValueError("TX point is required.")
    p["tx_lat"] = tx_point.y()
    p["tx_lon"] = tx_point.x()
    for key, attr in (
        ("tx_h", "TX_HEIGHT"), ("rx_h", "RX_HEIGHT"), ("f_mhz", "FREQ_MHZ"),
        ("radius_km", "RADIUS_KM"), ("time_pct", "TIME_PCT"),
        ("location_pct", "LOCATION_PCT"), ("situation_pct", "SITUATION_PCT"),
        ("tx_power", "TX_POWER"), ("tx_gain", "TX_GAIN"),
        ("rx_gain", "RX_GAIN"), ("cable_loss", "CABLE_LOSS"),
        ("rx_sens", "RX_SENSITIVITY"), ("antenna_bw", "ANTENNA_BW"),
        ("front_back_db", "FRONT_BACK_DB"), ("downtilt_deg", "DOWNTILT_DEG"),
        ("n0", "N0"), ("epsilon", "EPSILON"), ("sigma", "SIGMA"),
    ):
        p[key] = _dbl(parameters, getattr(alg, attr), context)
    p["grid_size"] = GRID_SIZE_PRESETS[_enum(parameters, alg.GRID_SIZE, context)]
    p["polarization"] = _enum(parameters, alg.POLARIZATION, context)
    p["climate"] = _enum(parameters, alg.CLIMATE, context)
    p["antenna_az"] = None
    if p["antenna_bw"] < 360.0:
        p["antenna_az"] = _dbl(parameters, alg.ANTENNA_AZ, context)
    p["antenna_preset"] = _enum(parameters, alg.ANTENNA_PRESET, context)
    p["h_pattern"] = alg.parameterAsFile(parameters, alg.H_PATTERN, context)
    p["v_pattern"] = alg.parameterAsFile(parameters, alg.V_PATTERN, context)
    p["clutter_enabled"] = _enum(parameters, alg.CLUTTER_MODEL, context) == 1
    p["clutter_raster_path"] = alg.parameterAsFile(
        parameters, alg.CLUTTER_RASTER, context
    )
    p["clutter_grid"] = (
        LandCoverGrid.from_raster(p["clutter_raster_path"])
        if p["clutter_raster_path"] else None
    )
    p["tx_clutter_override"] = clutter_override_value(
        _enum(parameters, alg.TX_CLUTTER_OVERRIDE, context)
    )
    p["rx_clutter_override"] = clutter_override_value(
        _enum(parameters, alg.RX_CLUTTER_OVERRIDE, context)
    )
    p["antenna_bw_override"] = (
        None if p["antenna_preset"] != 4 and p["antenna_bw"] == 360.0
        else p["antenna_bw"]
    )
    validate_itm_input_ranges(
        tx_height_m=p["tx_h"], rx_height_m=p["rx_h"], frequency_mhz=p["f_mhz"],
        surface_refractivity_n0=p["n0"], earth_conductivity_sigma=p["sigma"],
    )
    return p