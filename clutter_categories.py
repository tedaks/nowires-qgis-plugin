# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

"""Canonical clutter category definitions, WorldCover mappings, and loss tables.

This module is the single source of truth for the WorldCover class → category
mapping used by both simple and advanced clutter modes. Any changes to
_WORLDCOVER_MAP, _WORLDCOVER_TO_LEGACY_IDX, or _WORLDCOVER_TO_ADVANCED_IDX
must be reflected in all three and validated by
test_clutter_categories.py::test_simple_and_advanced_mappings_consistent.
"""

import numpy as np

ADVANCED_CLUTTER_CATEGORIES = (
    "open",
    "open_rural",
    "dense_rural",
    "vegetation",
    "suburban",
    "urban",
)

CLUTTER_CATEGORY_PARAMS = {
    "open": {
        "height_m": 0.0,
        "R_m": 10,
        "p2108_3_1_method": "2b",
        "p2108_3_2_applicable": False,
        "model": "none",
        "description": "Water, bare ground, snow/ice, wetland",
    },
    "open_rural": {
        "height_m": 2.0,
        "R_m": 10,
        "p2108_3_1_method": "2b",
        "p2108_3_2_applicable": False,
        "model": "p2108_height_gain",
        "description": "Grassland, cropland",
    },
    "dense_rural": {
        "height_m": 4.0,
        "R_m": 10,
        "p2108_3_1_method": "2b",
        "p2108_3_2_applicable": False,
        "model": "p2108_height_gain",
        "description": "Shrubland, moss/lichen",
    },
    "vegetation": {
        "height_m": 12.0,
        "R_m": 15,
        "p2108_3_1_method": "2a",
        "p2108_3_2_applicable": False,
        "model": "saalos",
        "description": "Tree cover, mangroves",
    },
    "suburban": {
        "height_m": 9.0,
        "R_m": 10,
        "p2108_3_1_method": "2a",
        "p2108_3_2_applicable": True,
        "model": "p2108_combined",
        "description": "Low-density built-up",
    },
    "urban": {
        "height_m": 15.0,
        "R_m": 20,
        "p2108_3_1_method": "2a",
        "p2108_3_2_applicable": True,
        "model": "p2108_combined",
        "description": "High-density built-up",
    },
}

_WORLDCOVER_MAP = {
    10: "vegetation",
    20: "dense_rural",
    30: "open_rural",
    40: "open_rural",
    50: "urban",
    60: "open",
    70: "open",
    80: "open",
    90: "open",
    95: "vegetation",
    100: "dense_rural",
}


def worldcover_class_to_advanced_category(class_id) -> str:
    try:
        return _WORLDCOVER_MAP.get(int(class_id), "open")
    except (TypeError, ValueError):
        return "open"


_LEGACY_TO_ADVANCED = {
    "open": "open",
    "rural": "open_rural",
    "vegetation": "vegetation",
    "suburban": "suburban",
    "urban": "urban",
    "open_rural": "open_rural",
    "dense_rural": "dense_rural",
}


def legacy_to_advanced_override(name):
    """Map a legacy simple-mode category to its advanced-mode counterpart."""
    return _LEGACY_TO_ADVANCED.get(name, "open")


# Legacy (simple-mode) category names and loss table.
LEGACY_CLUTTER_CATEGORIES: tuple[str, ...] = ("open", "rural", "vegetation", "suburban", "urban")
LEGACY_CLUTTER_LOSS_DB: dict[str, float] = {
    "open": 0.0, "rural": 2.0, "vegetation": 6.0,
    "suburban": 8.0, "urban": 10.0,
}

_LEGACY_CAT_IDX = {k: i for i, k in enumerate(LEGACY_CLUTTER_CATEGORIES)}
_LEGACY_CLUTTER_LOSS_ARRAY = np.array([
    LEGACY_CLUTTER_LOSS_DB["open"],
    LEGACY_CLUTTER_LOSS_DB["rural"],
    LEGACY_CLUTTER_LOSS_DB["vegetation"],
    LEGACY_CLUTTER_LOSS_DB["suburban"],
    LEGACY_CLUTTER_LOSS_DB["urban"],
], dtype=np.float64)

# Canonical lookup table: ESA WorldCover class ID (0-255) → legacy category index (0-4).
# CAUTION: Any change here must be reflected in _WORLDCOVER_MAP above and
# _WORLDCOVER_TO_ADVANCED_IDX below. Run test_clutter_categories.py to verify.
_WORLDCOVER_TO_LEGACY_IDX = np.zeros(256, dtype=np.int32)
_WORLDCOVER_TO_LEGACY_IDX[10] = _LEGACY_CAT_IDX["vegetation"]   # 2
_WORLDCOVER_TO_LEGACY_IDX[20] = _LEGACY_CAT_IDX["rural"]        # 1
_WORLDCOVER_TO_LEGACY_IDX[95] = _LEGACY_CAT_IDX["vegetation"]   # 2
_WORLDCOVER_TO_LEGACY_IDX[100] = _LEGACY_CAT_IDX["rural"]       # 1
_WORLDCOVER_TO_LEGACY_IDX[30] = _LEGACY_CAT_IDX["rural"]        # 1
_WORLDCOVER_TO_LEGACY_IDX[40] = _LEGACY_CAT_IDX["rural"]        # 1
_WORLDCOVER_TO_LEGACY_IDX[50] = _LEGACY_CAT_IDX["urban"]        # 4
_WORLDCOVER_TO_LEGACY_IDX[60] = _LEGACY_CAT_IDX["open"]         # 0
_WORLDCOVER_TO_LEGACY_IDX[70] = _LEGACY_CAT_IDX["open"]         # 0
_WORLDCOVER_TO_LEGACY_IDX[80] = _LEGACY_CAT_IDX["open"]         # 0
_WORLDCOVER_TO_LEGACY_IDX[90] = _LEGACY_CAT_IDX["open"]         # 0

# Canonical lookup table: ESA WorldCover class ID (0-255) → advanced category index (0-5).
_ADVANCED_CAT_IDX = {k: i for i, k in enumerate(ADVANCED_CLUTTER_CATEGORIES)}
_WORLDCOVER_TO_ADVANCED_IDX = np.zeros(256, dtype=np.int32)
_WORLDCOVER_TO_ADVANCED_IDX[10] = _ADVANCED_CAT_IDX["vegetation"]
_WORLDCOVER_TO_ADVANCED_IDX[20] = _ADVANCED_CAT_IDX["dense_rural"]
_WORLDCOVER_TO_ADVANCED_IDX[30] = _ADVANCED_CAT_IDX["open_rural"]
_WORLDCOVER_TO_ADVANCED_IDX[40] = _ADVANCED_CAT_IDX["open_rural"]
_WORLDCOVER_TO_ADVANCED_IDX[50] = _ADVANCED_CAT_IDX["urban"]
_WORLDCOVER_TO_ADVANCED_IDX[60] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[70] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[80] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[90] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[95] = _ADVANCED_CAT_IDX["vegetation"]
_WORLDCOVER_TO_ADVANCED_IDX[100] = _ADVANCED_CAT_IDX["dense_rural"]
