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


Batch analysis parameter dataclass for algorithm_batch.py.

Provides a typed ``BatchAnalysisParams`` container to replace the loose
dict previously constructed in ``_collect_batch_inputs``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from NoWires.defaults import DEFAULT_FREQ_MHZ
from NoWires.clutter.context import ClutterModel, BuildingType

if TYPE_CHECKING:
    from NoWires.clutter import LandCoverGrid
    from NoWires.elevation import ElevationGrid


@dataclass
class BatchAnalysisParams:
    mode: int = 0
    candidate_tx: list = field(default_factory=list)
    rx_points: list = field(default_factory=list)
    tx_h: float = 30.0
    rx_h: float = 10.0
    f_mhz: float = DEFAULT_FREQ_MHZ
    polarization: int = 1
    climate: int = 1
    time_pct: float = 50.0
    location_pct: float = 50.0
    situation_pct: float = 50.0
    tx_power: float = 43.0
    tx_gain_default: float = 8.0
    rx_gain_default: float = 2.0
    cable_loss: float = 2.0
    rx_sens: float = -100.0
    tx_default_preset_key: str = "omni"
    rx_default_preset_key: str = "omni"
    tx_default_az: float | None = None
    rx_default_az: float | None = None
    tx_front_back_db: float = 25.0
    rx_front_back_db: float = 25.0
    k_factor: float = 4.0 / 3.0
    n0: float = 301.0
    epsilon: float = 15.0
    sigma: float = 0.005
    clutter_enabled: bool = False
    clutter_grid: LandCoverGrid | None = None
    tx_clutter_override: str | None = None
    rx_clutter_override: str | None = None
    clutter_model: ClutterModel = "simple"
    cch_override_m: float | None = None
    clutter_percentile: float = 50.0
    street_width_m: float = 27.0
    bel_enabled: bool = False
    bel_building_type: BuildingType = "traditional"
    bel_elevation_angle_deg: float = 0.0
    owns_clutter_grid: bool = False
    elev: ElevationGrid | None = None
    total: int = 0