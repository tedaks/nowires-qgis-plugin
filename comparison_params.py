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
]

DELTA_STYLE_OPTIONS = ["diverging", "threshold"]
DELTA_THRESHOLD_DEFAULTS = [3.0, 5.0, 10.0]

_PANEL_KEYS = (
    "POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "RADIUS_KM",
    "GRID_SIZE", "POLARIZATION", "CLIMATE", "TIME_PCT",
    "LOCATION_PCT", "SITUATION_PCT", "TX_POWER", "TX_GAIN",
    "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY", "ANTENNA_BW",
    "ANTENNA_AZ", "ANTENNA_PRESET", "FRONT_BACK_DB", "DOWNTILT_DEG",
    "H_PATTERN", "V_PATTERN", "CLUTTER_MODEL", "CLUTTER_RASTER",
    "TX_CLUTTER_OVERRIDE", "RX_CLUTTER_OVERRIDE", "N0", "EPSILON", "SIGMA",
)

PANEL_A_CONSTANTS = {k: f"PANEL_A_{k}" for k in _PANEL_KEYS}
PANEL_B_CONSTANTS = {k: f"PANEL_B_{k}" for k in _PANEL_KEYS}

OUTPUT_CONSTANTS = {
    "OUTPUT_DIR": "OUTPUT_DIR",
    "DELTA_STYLE": "DELTA_STYLE",
    "DELTA_THRESHOLD_DB": "DELTA_THRESHOLD_DB",
    "OUTPUT_A": "OUTPUT_A",
    "OUTPUT_B": "OUTPUT_B",
    "OUTPUT_DELTA": "OUTPUT_DELTA",
    "OUTPUT_REPORT_HTML": "OUTPUT_REPORT_HTML",
}


def _num_param(name, desc, type=QgsProcessingParameterNumber.Double, **kw):
    return QgsProcessingParameterNumber(name, desc, type=type, **kw)


def make_panel_config():
    return {
        "point_param": lambda name, desc: _point_param(name, desc),
        "height_param": lambda name, desc, **kw: _num_param(name, desc, **kw),
        "freq_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=ITM_MIN_FREQUENCY_MHZ, maxValue=ITM_MAX_FREQUENCY_MHZ,
            **kw
        ),
        "radius_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=1.0, maxValue=500.0,
            **kw
        ),
        "pct_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=0.01, maxValue=99.99,
            **kw
        ),
        "dbm_param": lambda name, desc, **kw: _num_param(name, desc, **kw),
        "gain_param": lambda name, desc, **kw: _num_param(name, desc, **kw),
        "db_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=0.0,
            **kw
        ),
        "loss_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=0.0,
            **kw
        ),
        "az_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=0.0, maxValue=360.0,
            **kw
        ),
        "bw_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=1.0, maxValue=360.0,
            **kw
        ),
        "downtilt_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=-45.0, maxValue=45.0,
            **kw
        ),
        "n0_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=ITM_MIN_N0, maxValue=ITM_MAX_N0,
            **kw
        ),
        "epsilon_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=1.0,
            **kw
        ),
        "sigma_param": lambda name, desc, **kw: _num_param(
            name, desc, minValue=ITM_MIN_SIGMA,
            **kw
        ),
    }


def _point_param(name, desc):
    from qgis.core import QgsProcessingParameterPoint
    return QgsProcessingParameterPoint(name, desc)