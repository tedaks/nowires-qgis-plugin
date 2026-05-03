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


Coverage analysis parameter dataclass for algorithm_coverage.py.

Provides a typed ``CoverageAnalysisParams`` container to replace the
loose dict previously returned by ``extract_coverage_params``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .clutter import LandCoverGrid


@dataclass
class CoverageAnalysisParams:
    tx_lat: float = 0.0
    tx_lon: float = 0.0
    tx_h: float = 30.0
    rx_h: float = 10.0
    f_mhz: float = 300.0
    radius_km: float = 50.0
    grid_size: int = 192
    polarization: int = 1
    climate: int = 1
    time_pct: float = 50.0
    location_pct: float = 50.0
    situation_pct: float = 50.0
    tx_power: float = 43.0
    tx_gain: float = 8.0
    rx_gain: float = 2.0
    cable_loss: float = 2.0
    rx_sens: float = -100.0
    antenna_az: float | None = None
    antenna_bw_override: float | None = None
    antenna_preset: int = 0
    front_back_db: float = 25.0
    downtilt_deg: float = 0.0
    h_pattern: str = ""
    v_pattern: str = ""
    clutter_enabled: bool = False
    clutter_raster_path: str = ""
    clutter_grid: LandCoverGrid | None = None
    tx_clutter_override: str | None = None
    rx_clutter_override: str | None = None
    n0: float = 301.0
    epsilon: float = 15.0
    sigma: float = 0.005