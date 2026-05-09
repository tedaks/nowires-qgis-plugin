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

Terminal clutter correction helpers for NoWires.
"""

import logging
from dataclasses import dataclass

import numpy as np

from .worldcover_downloader import ensure_worldcover_for_area
from .clutter_advanced import (  # noqa: F401
    compute_terminal_clutter_loss, _category_height_m,
    _resolve_category_advanced, _legacy_to_advanced_override,
    compute_terminal_clutter_losses, _resolve_category,
)
from .clutter_grid import LandCoverGrid  # noqa: F401

logger = logging.getLogger(__name__)

LEGACY_CLUTTER_CATEGORIES = ("open", "rural", "vegetation", "suburban", "urban")
CLUTTER_CATEGORIES = LEGACY_CLUTTER_CATEGORIES
CLUTTER_LOSS_DB = {
    "open": 0.0,
    "rural": 2.0,
    "vegetation": 6.0,
    "suburban": 8.0,
    "urban": 10.0,
}
CLUTTER_MODEL_OPTIONS = [
    "Off",
    "Simple clutter correction",
    "Advanced clutter correction",
]
CLUTTER_OVERRIDE_OPTIONS = [
    "Auto",
    "open", "rural", "vegetation", "suburban", "urban",
    "open_rural", "dense_rural",
]

_CATEGORY_IDX = {k: i for i, k in enumerate(CLUTTER_CATEGORIES)}
_CLUTTER_LOSS_ARRAY = np.array([
    CLUTTER_LOSS_DB["open"],
    CLUTTER_LOSS_DB["rural"],
    CLUTTER_LOSS_DB["vegetation"],
    CLUTTER_LOSS_DB["suburban"],
    CLUTTER_LOSS_DB["urban"],
], dtype=np.float64)

# Lookup table: ESA WorldCover class ID (0-255) -> legacy category index (0-4).
# CAUTION: This LUT and _WORLDCOVER_ADVANCED_IDX in clutter_grid.py both
# encode the WorldCover class mapping. They MUST stay consistent with
# _WORLDVER_MAP in clutter_categories.py. When updating any one of them,
# update all three and run the dual-mapping consistency test
# (test_clutter_categories.py::test_simple_and_advanced_mappings_consistent).
_WORLDCOVER_TO_CATEGORY = np.zeros(256, dtype=np.int32)
_WORLDCOVER_TO_CATEGORY[10] = 2
_WORLDCOVER_TO_CATEGORY[20] = 1
_WORLDCOVER_TO_CATEGORY[95] = 2
_WORLDCOVER_TO_CATEGORY[100] = 1
_WORLDCOVER_TO_CATEGORY[30] = 1
_WORLDCOVER_TO_CATEGORY[40] = 1
_WORLDCOVER_TO_CATEGORY[50] = 4
_WORLDCOVER_TO_CATEGORY[60] = 0
_WORLDCOVER_TO_CATEGORY[70] = 0
_WORLDCOVER_TO_CATEGORY[80] = 0
_WORLDCOVER_TO_CATEGORY[90] = 0


def worldcover_class_to_clutter_category(class_id) -> str:
    raw = int(class_id)
    if raw < 0 or raw > 255:
        logger.warning("Unexpected WorldCover class ID %d (outside 0-255 range)", raw)
    return CLUTTER_CATEGORIES[_WORLDCOVER_TO_CATEGORY[raw % 256]]


def clutter_loss_db(category, frequency_mhz) -> float:
    del frequency_mhz
    return CLUTTER_LOSS_DB.get(category, 0.0)


def clutter_override_value(index_or_category) -> str | None:
    if index_or_category is None:
        return None
    if isinstance(index_or_category, str):
        return None if index_or_category == "Auto" else index_or_category
    idx = int(index_or_category)
    if idx < 0 or idx >= len(CLUTTER_OVERRIDE_OPTIONS):
        return None
    return CLUTTER_OVERRIDE_OPTIONS[idx]


def clutter_source_label(
    enabled,
    land_cover_grid=None,
    raster_path=None,
    tx_override=None,
    rx_override=None,
) -> str:
    """Return a user-visible source label for clutter reports."""
    if not enabled:
        return "off"
    sources = []
    if tx_override or rx_override:
        sources.append("override")
    if raster_path:
        sources.append(str(raster_path))
    elif land_cover_grid is not None:
        sources.append(land_cover_grid.source)
    if sources:
        return ",".join(sources)
    return "fallback_open"


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


def ensure_clutter_grid_for_area(south, north, west, east, feedback=None) -> LandCoverGrid | None:
    raster_path = ensure_worldcover_for_area(south, north, west, east, feedback=feedback)
    if raster_path is None:
        return None
    try:
        return LandCoverGrid.from_raster(raster_path)
    except RuntimeError:
        logger.warning("Failed to load downloaded WorldCover raster")
        return None