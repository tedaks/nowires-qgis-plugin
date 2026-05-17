# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import logging

from .clutter_categories import (
    legacy_to_advanced_override,
    worldcover_class_to_advanced_category,
)

logger = logging.getLogger(__name__)


_warned_low_vhf_p2108_combined = False


def _maybe_warn_low_vhf_p2108_combined(f_ghz, category):
    global _warned_low_vhf_p2108_combined
    if _warned_low_vhf_p2108_combined:
        return
    _warned_low_vhf_p2108_combined = True
    logger.warning(
        "P.2108 §3.2 invalid below 0.5 GHz; advanced clutter for category "
        "%s at %.3f GHz contributes 0 dB. Consider 'simple' mode for "
        "built-environment loss at low VHF.",
        category, f_ghz,
    )


def resolve_category_advanced(lat, lon, override, land_cover_grid):
    if override:
        return legacy_to_advanced_override(override), "override"
    if land_cover_grid is not None:
        class_id = land_cover_grid.sample_class(lat, lon)
        if class_id is not None:
            return worldcover_class_to_advanced_category(class_id), land_cover_grid.source
    return "open", "fallback_open"


def _resolve_category(lat, lon, override, land_cover_grid):
    if override:
        return override, "override"
    if land_cover_grid is not None:
        category = land_cover_grid.sample_category(lat, lon)
        if category is not None:
            return category, land_cover_grid.source
    return "open", "fallback_open"