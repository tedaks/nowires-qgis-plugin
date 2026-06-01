# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
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

 Licensed under the MIT License; see the LICENSE file for the full text.


Coverage Comparison Algorithm — Constants and config factory.

Extracted from algorithm_coverage_comparison.py for modularity.
"""

from __future__ import annotations

from dataclasses import dataclass

from qgis.core import QgsProcessingParameterNumber

from NoWires.antenna import CUSTOM_ANTENNA_PRESET_INDEX
from NoWires.clutter import clutter_override_value
from NoWires.clutter.context import BuildingType, ClutterModel
from NoWires.constants import (
    POLARIZATION_NAMES,
    GRID_SIZE_PRESETS,
    WGS84_CRS,
)
from NoWires.radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_N0,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MIN_SIGMA,
)

__all__ = [
    "GRID_SIZE_PRESETS",
    "POLARIZATION_NAMES",
    "DELTA_STYLE_DIVERGING",
    "DELTA_STYLE_THRESHOLD",
    "DELTA_STYLE_OPTIONS",
    "DELTA_THRESHOLD_DEFAULTS",
    "PANEL_A_CONSTANTS",
    "PANEL_B_CONSTANTS",
    "OUTPUT_CONSTANTS",
    "make_panel_config",
    "ComparisonPanelParams",
    "collect_panel_params",
]


@dataclass
class ComparisonPanelParams:
    tx_lat: float
    tx_lon: float
    tx_h: float
    rx_h: float
    f_mhz: float
    radius_km: float
    grid_size: int
    polarization: int
    climate: int
    time_pct: float
    location_pct: float
    situation_pct: float
    tx_power: float
    tx_gain: float
    rx_gain: float
    cable_loss: float
    rx_sens: float
    antenna_bw: float
    antenna_az: float | None
    antenna_preset: int
    front_back_db: float
    downtilt_deg: float
    h_pattern: str
    v_pattern: str
    clutter_enabled: bool
    clutter_model: ClutterModel
    cch_override_m: float | None
    clutter_percentile: float
    street_width_m: float
    bel_enabled: bool
    bel_building_type: BuildingType
    bel_elevation_angle_deg: float
    clutter_raster_path: str
    tx_clutter_override: str | None
    rx_clutter_override: str | None
    antenna_bw_override: float | None
    n0: float
    epsilon: float
    sigma: float


def collect_panel_params(algo, prefix: str, parameters, context) -> ComparisonPanelParams:
    """Read all per-panel QGIS parameters into a typed bundle.

    Centralises the ~35 parameterAs* reads that comparison_panel previously
    performed inline. Includes derived values (clutter_enabled,
    clutter_model, bel_building_type, cch_override_m, antenna_bw_override)
    so the caller never sees raw enum indices.

    Does NOT touch shared_clutter_grid or load LandCoverGrid — those depend
    on runtime state that lives in run_panel_coverage.
    """
    tx_point = algo.parameterAsPoint(parameters, f"{prefix}_POINT", context, crs=WGS84_CRS)
    if tx_point is None:
        raise ValueError(f"{prefix} TX point is required.")

    def pd(key: str):
        return algo.parameterAsDouble(parameters, f"{prefix}_{key}", context)

    def pe(key: str):
        return algo.parameterAsEnum(parameters, f"{prefix}_{key}", context)

    def pf(key: str):
        return algo.parameterAsFile(parameters, f"{prefix}_{key}", context)

    def pb(key: str):
        return algo.parameterAsBool(parameters, f"{prefix}_{key}", context)

    antenna_bw = pd("ANTENNA_BW")
    antenna_preset = pe("ANTENNA_PRESET")
    antenna_bw_override: float | None
    antenna_az: float | None
    if antenna_preset == 0:
        antenna_az = None
        antenna_bw_override = 360.0
    else:
        antenna_az = pd("ANTENNA_AZ") if antenna_bw < 360.0 else None
        antenna_bw_override = (
            None
            if antenna_preset != CUSTOM_ANTENNA_PRESET_INDEX and antenna_bw == 360.0
            else antenna_bw
        )

    clutter_model_idx = pe("CLUTTER_MODEL")
    cch_raw = pd("CCH_OVERRIDE")
    bel_building_type_idx = pe("BEL_BUILDING_TYPE")

    return ComparisonPanelParams(
        tx_lat=tx_point.y(), tx_lon=tx_point.x(),
        tx_h=pd("TX_HEIGHT"), rx_h=pd("RX_HEIGHT"),
        f_mhz=pd("FREQ_MHZ"), radius_km=pd("RADIUS_KM"),
        grid_size=GRID_SIZE_PRESETS[pe("GRID_SIZE")],
        polarization=pe("POLARIZATION"), climate=pe("CLIMATE"),
        time_pct=pd("TIME_PCT"), location_pct=pd("LOCATION_PCT"),
        situation_pct=pd("SITUATION_PCT"),
        tx_power=pd("TX_POWER"), tx_gain=pd("TX_GAIN"),
        rx_gain=pd("RX_GAIN"), cable_loss=pd("CABLE_LOSS"),
        rx_sens=pd("RX_SENSITIVITY"),
        antenna_bw=antenna_bw, antenna_az=antenna_az,
        antenna_preset=antenna_preset, front_back_db=pd("FRONT_BACK_DB"),
        downtilt_deg=pd("DOWNTILT_DEG"),
        h_pattern=pf("H_PATTERN"), v_pattern=pf("V_PATTERN"),
        clutter_enabled=clutter_model_idx > 0,
        clutter_model="advanced" if clutter_model_idx == 2 else "simple",
        cch_override_m=cch_raw if cch_raw > 0.0 else None,
        clutter_percentile=pd("CLUTTER_PERCENTILE"),
        street_width_m=pd("STREET_WIDTH_M"),
        bel_enabled=pb("BEL_ENABLED"),
        bel_building_type=(
            "traditional" if bel_building_type_idx == 0 else "thermally_efficient"
        ),
        bel_elevation_angle_deg=pd("BEL_ELEVATION_ANGLE"),
        clutter_raster_path=pf("CLUTTER_RASTER"),
        tx_clutter_override=clutter_override_value(pe("TX_CLUTTER_OVERRIDE")),
        rx_clutter_override=clutter_override_value(pe("RX_CLUTTER_OVERRIDE")),
        antenna_bw_override=antenna_bw_override,
        n0=pd("N0"), epsilon=pd("EPSILON"), sigma=pd("SIGMA"),
    )

DELTA_STYLE_DIVERGING = "diverging"
DELTA_STYLE_THRESHOLD = "threshold"
DELTA_STYLE_OPTIONS = [DELTA_STYLE_DIVERGING, DELTA_STYLE_THRESHOLD]
DELTA_THRESHOLD_DEFAULTS = [3.0, 5.0, 10.0]

_PANEL_KEYS = (
    "POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "RADIUS_KM",
    "GRID_SIZE", "POLARIZATION", "CLIMATE", "TIME_PCT",
    "LOCATION_PCT", "SITUATION_PCT", "TX_POWER", "TX_GAIN",
    "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY", "ANTENNA_BW",
    "ANTENNA_AZ", "ANTENNA_PRESET", "FRONT_BACK_DB", "DOWNTILT_DEG",
    "H_PATTERN", "V_PATTERN", "CLUTTER_MODEL", "CLUTTER_RASTER",
    "TX_CLUTTER_OVERRIDE", "RX_CLUTTER_OVERRIDE", "CCH_OVERRIDE", "N0", "EPSILON", "SIGMA",
)

PANEL_A_CONSTANTS = {f"PANEL_A_{k}": f"PANEL_A_{k}" for k in _PANEL_KEYS}
PANEL_B_CONSTANTS = {f"PANEL_B_{k}": f"PANEL_B_{k}" for k in _PANEL_KEYS}

OUTPUT_CONSTANTS = {
    "OUTPUT_DIR": "OUTPUT_DIR",
    "DELTA_STYLE": "DELTA_STYLE",
    "DELTA_THRESHOLD_DB": "DELTA_THRESHOLD_DB",
    "OUTPUT_A": "OUTPUT_A",
    "OUTPUT_B": "OUTPUT_B",
    "OUTPUT_DELTA": "OUTPUT_DELTA",
    "OUTPUT_REPORT_HTML": "OUTPUT_REPORT_HTML",
}


def _num_param(name, desc, type=QgsProcessingParameterNumber.Type.Double, **kw):
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
