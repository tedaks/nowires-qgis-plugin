# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Shared case definitions and synthetic elevation for benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class CoverageCase:
    label: str
    radius_km: float
    grid_size: int
    frequency_mhz: float


@dataclass(frozen=True)
class P2PCase:
    label: str
    distance_km: float
    terrain: Literal["flat", "varied", "coastal"]
    frequency_mhz: float
    tx_height_m: float = 30.0
    rx_height_m: float = 10.0
    climate_idx: int = 1
    polarization: int = 0
    epsilon: float = 15.0
    sigma: float = 0.005
    time_pct: float = 50.0
    location_pct: float = 50.0
    situation_pct: float = 50.0
    eirp_dbm: float = 30.0
    ant_gain_adj: float = 0.0
    rx_gain_dbi: float = 0.0


COVERAGE_CASES = (
    CoverageCase("small", radius_km=2.0, grid_size=64, frequency_mhz=900.0),
    CoverageCase("medium", radius_km=5.0, grid_size=128, frequency_mhz=1800.0),
    CoverageCase("large", radius_km=8.0, grid_size=192, frequency_mhz=3500.0),
)

P2P_CASES = (
    P2PCase("short_rural", distance_km=1.0, terrain="flat", frequency_mhz=900.0),
    P2PCase("medium_urban", distance_km=5.0, terrain="varied", frequency_mhz=1800.0),
    P2PCase("long_los", distance_km=20.0, terrain="coastal", frequency_mhz=3500.0),
)


class SyntheticElevationGrid:
    """Deterministic in-memory DEM for repeatable benchmark runs."""

    def __init__(self, radius_km: float, samples: int = 512):
        radius_deg = radius_km / 111.32
        self.min_lat = -radius_deg
        self.max_lat = radius_deg
        self.min_lon = -radius_deg
        self.max_lon = radius_deg
        self.n_rows = samples
        self.n_cols = samples

        ys = np.linspace(-1.0, 1.0, samples, dtype=np.float32)
        xs = np.linspace(-1.0, 1.0, samples, dtype=np.float32)
        xg, yg = np.meshgrid(xs, ys)
        ridge = 180.0 * np.exp(-3.5 * (xg * xg + yg * yg))
        ripple = 35.0 * np.sin(8.0 * xg) * np.cos(6.0 * yg)
        slope = 25.0 * (xg + yg)
        self.data = (ridge + ripple + slope + 120.0).astype(np.float32)

    def grid_meta_dict(self):
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "n_lat": self.n_rows,
            "n_lon": self.n_cols,
        }

    def sample(self, lat, lon):
        fy = (self.max_lat - lat) / (self.max_lat - self.min_lat) * (self.n_rows - 1)
        fx = (lon - self.min_lon) / (self.max_lon - self.min_lon) * (self.n_cols - 1)
        if fy < 0 or fx < 0 or fy > self.n_rows - 1 or fx > self.n_cols - 1:
            return float("nan")
        y0 = int(fy)
        x0 = int(fx)
        y1 = min(y0 + 1, self.n_rows - 1)
        x1 = min(x0 + 1, self.n_cols - 1)
        ty = fy - y0
        tx = fx - x0
        v00 = self.data[y0, x0]
        v01 = self.data[y0, x1]
        v10 = self.data[y1, x0]
        v11 = self.data[y1, x1]
        return v00 * (1 - tx) * (1 - ty) + v01 * tx * (1 - ty) + v10 * (1 - tx) * ty + v11 * tx * ty

    def sample_line(self, lat1, lon1, lat2, lon2, n_points):
        ts = np.linspace(0.0, 1.0, n_points)
        lats = lat1 + ts * (lat2 - lat1)
        lons = lon1 + ts * (lon2 - lon1)
        fy = np.clip(
            (self.max_lat - lats) / (self.max_lat - self.min_lat) * (self.n_rows - 1),
            0, self.n_rows - 1 - 1e-9
        )
        fx = np.clip(
            (lons - self.min_lon) / (self.max_lon - self.min_lon) * (self.n_cols - 1),
            0, self.n_cols - 1 - 1e-9
        )
        y0 = np.floor(fy).astype(int)
        x0 = np.floor(fx).astype(int)
        y1 = np.clip(y0 + 1, 0, self.n_rows - 1)
        x1 = np.clip(x0 + 1, 0, self.n_cols - 1)
        ty = (fy - y0).astype(np.float32)
        tx_ = (fx - x0).astype(np.float32)
        return (
            self.data[y0, x0] * (1 - tx_) * (1 - ty)
            + self.data[y0, x1] * tx_ * (1 - ty)
            + self.data[y1, x0] * (1 - tx_) * ty
            + self.data[y1, x1] * tx_ * ty
        )
