# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Terminal clutter correction helpers for NoWires."""

from __future__ import annotations

import logging

from NoWires.worldcover_downloader import ensure_worldcover_for_area
from NoWires.clutter.categories import (  # noqa: F401
    LEGACY_CLUTTER_CATEGORIES,
    LEGACY_CLUTTER_LOSS_DB,
    _WORLDCOVER_TO_LEGACY_IDX,
    _LEGACY_CAT_IDX,
    _LEGACY_CLUTTER_LOSS_ARRAY,
    legacy_to_advanced_override,
)
from NoWires.clutter.context import TerminalClutterLosses  # noqa: F401
from NoWires.clutter.advanced import (  # noqa: F401
    compute_terminal_clutter_loss, _category_height_m,
    compute_terminal_clutter_losses,
    compute_path_clutter_loss, ClutterComponents,
    compute_advanced_loss,
)
from NoWires.clutter.resolve import (  # noqa: F401
    resolve_category_advanced,
    _resolve_category,
)
from NoWires.clutter.grid import LandCoverGrid  # noqa: F401

logger = logging.getLogger(__name__)

CLUTTER_CATEGORIES: tuple[str, ...] = LEGACY_CLUTTER_CATEGORIES
CLUTTER_LOSS_DB: dict[str, float] = LEGACY_CLUTTER_LOSS_DB
# Re-export the canonical lookup table from clutter_categories for use
# by clutter_grid.py and any other consumer that needs vectorised lookups.
_WORLDCOVER_TO_CATEGORY = _WORLDCOVER_TO_LEGACY_IDX
_CATEGORY_IDX = _LEGACY_CAT_IDX
_CLUTTER_LOSS_ARRAY = _LEGACY_CLUTTER_LOSS_ARRAY

CLUTTER_MODEL_OPTIONS = [
    "Off",
    "Simple clutter correction",
    "Advanced clutter correction",
]
CLUTTER_OVERRIDE_AUTO = "Auto"
CLUTTER_OVERRIDE_OPTIONS = [
    CLUTTER_OVERRIDE_AUTO,
    "open", "rural", "vegetation", "suburban", "urban",
    "open_rural", "dense_rural",
]


def worldcover_class_to_clutter_category(class_id) -> str:
    raw = int(class_id)
    if raw < 0 or raw > 255:
        logger.warning("Unexpected WorldCover class ID %d (outside 0-255 range)", raw)
        return "open"
    return CLUTTER_CATEGORIES[int(_WORLDCOVER_TO_CATEGORY[raw])]


def clutter_loss_db(category, frequency_mhz) -> float:
    del frequency_mhz
    return CLUTTER_LOSS_DB.get(category, 0.0)


def clutter_override_value(index_or_category) -> str | None:
    if index_or_category is None:
        return None
    if isinstance(index_or_category, str):
        return None if index_or_category == CLUTTER_OVERRIDE_AUTO else index_or_category
    idx = int(index_or_category)
    if idx < 0 or idx >= len(CLUTTER_OVERRIDE_OPTIONS):
        return None
    value = CLUTTER_OVERRIDE_OPTIONS[idx]
    return None if value == CLUTTER_OVERRIDE_AUTO else value


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


def ensure_clutter_grid_for_area(south: float, north: float, west: float, east: float,
                                 feedback: object | None = None) -> LandCoverGrid | None:
    raster_path = ensure_worldcover_for_area(south, north, west, east, feedback=feedback)
    if raster_path is None:
        return None
    try:
        # LandCoverGrid.from_raster is a classmethod that returns Any-typed
        # GDAL handles internally; mypy can't narrow to LandCoverGrid here.
        return LandCoverGrid.from_raster(raster_path)  # type: ignore[no-any-return]
    except RuntimeError:
        logger.warning("Failed to load downloaded WorldCover raster")
        return None
