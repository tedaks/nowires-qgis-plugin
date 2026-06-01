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


P2P analysis parameter object for run_p2p_analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from NoWires.clutter.context import ClutterModel, BuildingType

if TYPE_CHECKING:
    from NoWires.antenna import AntennaConfig
    from NoWires.clutter import LandCoverGrid


@dataclass
class P2PAnalysisParams:
    tx_lat: float
    tx_lon: float
    rx_lat: float
    rx_lon: float
    tx_h: float
    rx_h: float
    f_mhz: float
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
    k_factor: float
    n0: float
    epsilon: float
    sigma: float
    tx_antenna_config: AntennaConfig | None = field(default=None)
    rx_antenna_config: AntennaConfig | None = field(default=None)
    clutter_enabled: bool = False
    clutter_grid: LandCoverGrid | None = None
    tx_clutter_override: str | None = "open"
    rx_clutter_override: str | None = "open"
    clutter_model: ClutterModel = "simple"
    cch_override_m: float | None = None
    clutter_percentile: float = 50.0
    street_width_m: float = 27.0
    bel_enabled: bool = False
    bel_building_type: BuildingType = "traditional"
    bel_elevation_angle_deg: float = 0.0
    profile_dest: str = ""
    fresnel_dest: str = ""
    markers_dest: str = ""
    report_csv_path: str = ""
    report_json_path: str = ""
    report_html_path: str = ""
    show_chart: bool = True
    context: Any = field(default=None)
    feedback: Any = field(default=None)
    output_profile: str = ""
    output_fresnel: str = ""
    output_markers: str = ""
    output_report_csv: str = ""
    output_report_json: str = ""
    output_report_html: str = ""
    post_processor_sink: list[str] = field(default_factory=list)
    _pending_chart_kwargs: dict | None = field(default=None)
