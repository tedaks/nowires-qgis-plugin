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


P2P analysis parameter object for run_p2p_analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .antenna import AntennaConfig
    from .clutter import LandCoverGrid


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
    tx_clutter_override: str = "open"
    rx_clutter_override: str = "open"
    clutter_model: str = "simple"
    cch_override_m: float | None = None
    profile_dest: str = ""
    fresnel_dest: str = ""
    markers_dest: str = ""
    report_csv_path: str = ""
    report_json_path: str = ""
    report_html_path: str = ""
    show_chart: bool = True
    context: object = field(default=None)
    feedback: object = field(default=None)
    output_profile: str = ""
    output_fresnel: str = ""
    output_markers: str = ""
    output_report_csv: str = ""
    output_report_json: str = ""
    output_report_html: str = ""