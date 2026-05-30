# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ClutterModel = Literal["simple", "advanced"]
BuildingType = Literal["traditional", "thermally_efficient"]

_VALID_MODELS: tuple[ClutterModel, ...] = ("simple", "advanced")


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
    method: ClutterModel = "simple"
    percentile: float = 50.0


@dataclass(frozen=True)
class ClutterLossContext:
    frequency_mhz: float
    distance_m: float
    tx_height_m: float
    rx_height_m: float
    cch_override_m: float | None = None
    model: ClutterModel = "simple"
    percentile: float = 50.0
    street_width_m: float = 27.0
    bel_enabled: bool = False
    bel_building_type: BuildingType = "traditional"
    bel_elevation_angle_deg: float = 0.0

    def __post_init__(self):
        if self.model not in _VALID_MODELS:
            raise ValueError(
                f"ClutterLossContext.model must be one of {_VALID_MODELS}, got {self.model!r}"
            )


def build_initial_clutter_context(
    *, frequency_mhz: float, tx_height_m: float, rx_height_m: float,
    cch_override_m: float | None,
    model: ClutterModel, percentile: float, street_width_m: float,
    bel_enabled: bool, bel_building_type: BuildingType, bel_elevation_angle_deg: float,
) -> ClutterLossContext:
    """Build a ClutterLossContext with distance=0 placeholder.

    Per-pixel distance is filled in later during task building (coverage) or
    per-link recomputation (P2P/batch). The single factory keeps the placeholder
    semantics consistent between algorithm and engine callers.
    """
    return ClutterLossContext(
        frequency_mhz=frequency_mhz, distance_m=0.0,
        tx_height_m=tx_height_m, rx_height_m=rx_height_m,
        cch_override_m=cch_override_m, model=model,
        percentile=percentile, street_width_m=street_width_m,
        bel_enabled=bel_enabled, bel_building_type=bel_building_type,
        bel_elevation_angle_deg=bel_elevation_angle_deg,
    )


def build_link_clutter_context(
    *, params, dist_m: float, tx_h: float, rx_h: float,
) -> ClutterLossContext:
    """Build a per-link ClutterLossContext from a params object.

    Duck-types over P2PAnalysisParams and BatchAnalysisParams: both expose
    f_mhz, cch_override_m, clutter_model, clutter_percentile,
    street_width_m, bel_enabled, bel_building_type, bel_elevation_angle_deg.
    tx_h/rx_h are explicit because batch overrides per-link from feature
    attributes; the rest are read from params directly.
    """
    return ClutterLossContext(
        frequency_mhz=params.f_mhz, distance_m=dist_m,
        tx_height_m=tx_h, rx_height_m=rx_h,
        cch_override_m=params.cch_override_m,
        model=params.clutter_model, percentile=params.clutter_percentile,
        street_width_m=params.street_width_m, bel_enabled=params.bel_enabled,
        bel_building_type=params.bel_building_type,
        bel_elevation_angle_deg=params.bel_elevation_angle_deg,
    )
