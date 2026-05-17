# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from dataclasses import dataclass

_VALID_MODELS = ("simple", "advanced")


@dataclass(frozen=True)
class TerminalClutterLosses:
    tx_category: str
    rx_category: str
    tx_loss_db: float
    rx_loss_db: float
    total_loss_db: float
    source: str
    tx_cch_m: float = 0.0
    rx_cch_m: float = 0.0
    tx_bel_db: float = 0.0
    rx_bel_db: float = 0.0
    total_with_bel_db: float = 0.0
    method: str = "simple"
    percentile: float = 50.0


@dataclass(frozen=True)
class ClutterLossContext:
    frequency_mhz: float
    distance_m: float
    tx_height_m: float
    rx_height_m: float
    rx_ground_elevation_m: float = 0.0
    tx_ground_elevation_m: float = 0.0
    polarization: int = 0
    cch_override_m: float | None = None
    model: str = "simple"
    percentile: float = 50.0
    street_width_m: float = 27.0
    bel_enabled: bool = False
    bel_building_type: str = "traditional"
    bel_elevation_angle_deg: float = 0.0

    def __post_init__(self):
        if self.model not in _VALID_MODELS:
            raise ValueError(
                f"ClutterLossContext.model must be one of {_VALID_MODELS}, got {self.model!r}"
            )


def build_initial_clutter_context(
    *, frequency_mhz: float, tx_height_m: float, rx_height_m: float,
    tx_ground_elevation_m: float, polarization: int, cch_override_m: float | None,
    model: str, percentile: float, street_width_m: float,
    bel_enabled: bool, bel_building_type: str, bel_elevation_angle_deg: float,
) -> ClutterLossContext:
    """Build a ClutterLossContext with distance=0 and rx_ground=0 placeholders.

    Per-pixel rx_ground and distance are filled in later during task building
    (coverage) or per-link recomputation (P2P/batch). The single factory keeps
    the placeholder semantics consistent between algorithm and engine callers.
    """
    return ClutterLossContext(
        frequency_mhz=frequency_mhz, distance_m=0.0,
        tx_height_m=tx_height_m, rx_height_m=rx_height_m,
        rx_ground_elevation_m=0.0, tx_ground_elevation_m=tx_ground_elevation_m,
        polarization=polarization, cch_override_m=cch_override_m, model=model,
        percentile=percentile, street_width_m=street_width_m,
        bel_enabled=bel_enabled, bel_building_type=bel_building_type,
        bel_elevation_angle_deg=bel_elevation_angle_deg,
    )