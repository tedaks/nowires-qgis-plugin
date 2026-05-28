# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dataclass for P2P profile chart parameters."""

from dataclasses import dataclass

import numpy as np

from NoWires.p2p.analysis_params import P2PAnalysisParams


@dataclass
class P2PProfileParams:
    cfg: P2PAnalysisParams
    distances: np.ndarray
    elevations: np.ndarray
    terrain_bulge: np.ndarray
    los_h: np.ndarray
    fresnel_r: np.ndarray
    dist_m: float
    result: object
    prx_dbm: float
    margin_db: float
    itm_loss_db: float | None = None
