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


Coverage Algorithm — Parameter definitions and constants.

Extracted from algorithm_coverage.py for modularity.
"""

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterRasterDestination,
    QgsCoordinateReferenceSystem,
)
from .defaults import (
    DEFAULT_ANTENNA_AZIMUTH,
    DEFAULT_ANTENNA_BEAMWIDTH,
    DEFAULT_DOWNTILT_DEG,
    DEFAULT_FREQ_MHZ,
    DEFAULT_FRONT_BACK_DB,
    DEFAULT_RADIUS_KM,
    DEFAULT_RX_HEIGHT_M,
    DEFAULT_TIME_PCT,
    DEFAULT_TX_HEIGHT_M,
)
from .radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_TERMINAL_HEIGHT_M,
    validate_itm_input_ranges,
)
from .antenna import ANTENNA_PRESET_OPTIONS, CUSTOM_ANTENNA_PRESET_INDEX
from .clutter import LandCoverGrid, clutter_override_value
from .constants import (
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
    "RX_CLUTTER_OVERRIDE", "CCH_OVERRIDE",
    "CLUTTER_PERCENTILE", "STREET_WIDTH", "BEL_ENABLED", "BEL_BUILDING_TYPE",
    "BEL_ELEVATION_ANGLE",
    "N0", "EPSILON", "SIGMA", "OUTPUT_RASTER",
    "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON", "OUTPUT_REPORT_HTML",
)
PARAM_CONSTANTS = {k: k for k in _PARAM_NAMES}


_DBL = QgsProcessingParameterNumber.Type.Double


def _add_basic_params(alg):
    alg.addParameter(QgsProcessingParameterPoint(
        alg.TX_POINT, "Transmitter (TX) point"))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.TX_HEIGHT, "TX antenna height (m)", type=_DBL, defaultValue=DEFAULT_TX_HEIGHT_M,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.RX_HEIGHT, "RX antenna height (m)", type=_DBL, defaultValue=DEFAULT_RX_HEIGHT_M,
        minValue=ITM_MIN_TERMINAL_HEIGHT_M, maxValue=ITM_MAX_TERMINAL_HEIGHT_M))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.FREQ_MHZ, "Frequency (MHz)", type=_DBL, defaultValue=DEFAULT_FREQ_MHZ,
        minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.RADIUS_KM, "Max analysis distance (km)", type=_DBL,
        defaultValue=DEFAULT_RADIUS_KM, minValue=1.0, maxValue=500.0))
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
            attr, label, type=_DBL, defaultValue=DEFAULT_TIME_PCT, minValue=0.01, maxValue=99.99))


def _add_antenna_params(alg):
    alg.addParameter(QgsProcessingParameterNumber(
        alg.ANTENNA_AZ, "Antenna azimuth (deg, blank=omni)", type=_DBL,
        defaultValue=DEFAULT_ANTENNA_AZIMUTH, minValue=0.0, maxValue=360.0, optional=True))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.ANTENNA_BW, "Antenna beamwidth (deg)", type=_DBL,
        defaultValue=DEFAULT_ANTENNA_BEAMWIDTH, minValue=1.0, maxValue=360.0))
    alg.addParameter(QgsProcessingParameterEnum(
        alg.ANTENNA_PRESET, "TX antenna preset",
        options=ANTENNA_PRESET_OPTIONS, defaultValue=0))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.FRONT_BACK_DB, "TX front-to-back ratio (dB)", type=_DBL,
        defaultValue=DEFAULT_FRONT_BACK_DB, minValue=0.0))
    alg.addParameter(QgsProcessingParameterNumber(
        alg.DOWNTILT_DEG, "TX downtilt (deg)", type=_DBL,
        defaultValue=DEFAULT_DOWNTILT_DEG, minValue=-45.0, maxValue=45.0))
    alg.addParameter(QgsProcessingParameterFile(
        alg.H_PATTERN, "TX horizontal pattern CSV", extension="csv", optional=True))
    alg.addParameter(QgsProcessingParameterFile(
        alg.V_PATTERN, "TX vertical pattern CSV", extension="csv", optional=True))


def _add_output_params(alg):
    alg.addParameter(QgsProcessingParameterRasterDestination(
        alg.OUTPUT_RASTER, "Coverage raster output"))
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
    from qgis.core import QgsProcessingException
    from .coverage_analysis_params import CoverageAnalysisParams
    _dbl = alg.parameterAsDouble
    _enum = alg.parameterAsEnum
    _bool = alg.parameterAsBool
    tx_point = alg.parameterAsPoint(
        parameters, alg.TX_POINT, context,
        crs=QgsCoordinateReferenceSystem("EPSG:4326"),
    )
    if tx_point is None:
        raise QgsProcessingException("TX point is required.")
    doubles = {}
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
        doubles[key] = _dbl(parameters, getattr(alg, attr), context)
    grid_size = GRID_SIZE_PRESETS[_enum(parameters, alg.GRID_SIZE, context)]
    polarization = _enum(parameters, alg.POLARIZATION, context)
    climate = _enum(parameters, alg.CLIMATE, context)
    antenna_az = None
    if doubles["antenna_bw"] < 360.0:
        antenna_az = _dbl(parameters, alg.ANTENNA_AZ, context)
    antenna_preset = _enum(parameters, alg.ANTENNA_PRESET, context)
    h_pattern = alg.parameterAsFile(parameters, alg.H_PATTERN, context)
    v_pattern = alg.parameterAsFile(parameters, alg.V_PATTERN, context)
    clutter_model_idx = _enum(parameters, alg.CLUTTER_MODEL, context)
    clutter_enabled = clutter_model_idx > 0
    clutter_model = "advanced" if clutter_model_idx == 2 else "simple"
    cch_raw = _dbl(parameters, alg.CCH_OVERRIDE, context)
    cch_override_m = cch_raw if cch_raw > 0.0 else None
    clutter_raster_path = alg.parameterAsFile(
        parameters, alg.CLUTTER_RASTER, context
    )
    clutter_grid = (
        LandCoverGrid.from_raster(clutter_raster_path)
        if clutter_raster_path else None
    )
    tx_clutter_override = clutter_override_value(
        _enum(parameters, alg.TX_CLUTTER_OVERRIDE, context)
    )
    rx_clutter_override = clutter_override_value(
        _enum(parameters, alg.RX_CLUTTER_OVERRIDE, context)
    )
    clutter_percentile = _dbl(parameters, alg.CLUTTER_PERCENTILE, context)
    street_width_m = _dbl(parameters, alg.STREET_WIDTH, context)
    bel_enabled = _bool(parameters, alg.BEL_ENABLED, context)
    bel_building_type_idx = _enum(parameters, alg.BEL_BUILDING_TYPE, context)
    bel_building_type = "traditional" if bel_building_type_idx == 0 else "thermally_efficient"
    bel_elevation_angle = _dbl(parameters, alg.BEL_ELEVATION_ANGLE, context)
    antenna_bw_override = (
        None if antenna_preset != CUSTOM_ANTENNA_PRESET_INDEX and doubles["antenna_bw"] == 360.0
        else doubles["antenna_bw"]
    )
    try:
        validate_itm_input_ranges(
            tx_height_m=doubles["tx_h"], rx_height_m=doubles["rx_h"],
            frequency_mhz=doubles["f_mhz"],
            surface_refractivity_n0=doubles["n0"],
            earth_conductivity_sigma=doubles["sigma"],
        )
    except ValueError as exc:
        raise QgsProcessingException(str(exc))
    return CoverageAnalysisParams(
        tx_lat=tx_point.y(), tx_lon=tx_point.x(),
        tx_h=doubles["tx_h"], rx_h=doubles["rx_h"],
        f_mhz=doubles["f_mhz"], radius_km=doubles["radius_km"],
        grid_size=grid_size, polarization=polarization, climate=climate,
        time_pct=doubles["time_pct"], location_pct=doubles["location_pct"],
        situation_pct=doubles["situation_pct"], tx_power=doubles["tx_power"],
        tx_gain=doubles["tx_gain"], rx_gain=doubles["rx_gain"],
        cable_loss=doubles["cable_loss"], rx_sens=doubles["rx_sens"],
        antenna_az=antenna_az, antenna_bw_override=antenna_bw_override,
        antenna_preset=antenna_preset, front_back_db=doubles["front_back_db"],
        downtilt_deg=doubles["downtilt_deg"], h_pattern=h_pattern,
        v_pattern=v_pattern, clutter_enabled=clutter_enabled,
        clutter_raster_path=clutter_raster_path, clutter_grid=clutter_grid,
        tx_clutter_override=tx_clutter_override,
        rx_clutter_override=rx_clutter_override,
        clutter_model=clutter_model,
        cch_override_m=cch_override_m,
        clutter_percentile=clutter_percentile,
        street_width_m=street_width_m,
        bel_enabled=bel_enabled,
        bel_building_type=bel_building_type,
        bel_elevation_angle_deg=bel_elevation_angle,
        n0=doubles["n0"], epsilon=doubles["epsilon"], sigma=doubles["sigma"],
    )
