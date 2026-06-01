# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
import pytest
from clutter.categories import (
    ADVANCED_CLUTTER_CATEGORIES,
    CLUTTER_CATEGORY_PARAMS,
    _LEGACY_TO_ADVANCED,
    legacy_to_advanced_override,
    worldcover_class_to_advanced_category,
)


@pytest.mark.parametrize("class_id,expected", [
    (10, "vegetation"),
    (20, "dense_rural"),
    (30, "open_rural"),
    (40, "open_rural"),
    (50, "urban"),
    (60, "open"),
    (70, "open"),
    (80, "open"),
    (90, "open"),
    (95, "vegetation"),
    (100, "dense_rural"),
])
def test_worldcover_mapping(class_id, expected):
    assert worldcover_class_to_advanced_category(class_id) == expected


def test_unknown_class_defaults_to_open():
    assert worldcover_class_to_advanced_category(999) == "open"
    assert worldcover_class_to_advanced_category(-1) == "open"


def test_all_categories_have_required_params():
    for cat in ADVANCED_CLUTTER_CATEGORIES:
        params = CLUTTER_CATEGORY_PARAMS[cat]
        assert "height_m" in params
        assert "R_m" in params
        assert "p2108_3_1_method" in params
        assert "p2108_3_2_applicable" in params
        assert "model" in params
        assert params["model"] in (
            "none", "p833", "p2108_height_gain", "p2108_combined",
        )


def test_category_model_assignments():
    assert CLUTTER_CATEGORY_PARAMS["vegetation"]["model"] == "p833"
    assert CLUTTER_CATEGORY_PARAMS["urban"]["model"] == "p2108_combined"
    assert CLUTTER_CATEGORY_PARAMS["suburban"]["model"] == "p2108_combined"
    assert CLUTTER_CATEGORY_PARAMS["open"]["model"] == "none"
    assert CLUTTER_CATEGORY_PARAMS["open"]["height_m"] == 0.0
    assert CLUTTER_CATEGORY_PARAMS["open_rural"]["model"] == "p2108_height_gain"


def test_p2108_3_2_applicable_flags():
    assert CLUTTER_CATEGORY_PARAMS["urban"]["p2108_3_2_applicable"] is True
    assert CLUTTER_CATEGORY_PARAMS["suburban"]["p2108_3_2_applicable"] is True
    assert CLUTTER_CATEGORY_PARAMS["open"]["p2108_3_2_applicable"] is False
    assert CLUTTER_CATEGORY_PARAMS["open_rural"]["p2108_3_2_applicable"] is False


def test_legacy_to_advanced_mapping_covers_all_legacy_categories():
    for cat in ("open", "rural", "vegetation", "suburban", "urban"):
        assert cat in _LEGACY_TO_ADVANCED
        result = legacy_to_advanced_override(cat)
        assert result in ADVANCED_CLUTTER_CATEGORIES


def test_legacy_to_advanced_is_idempotent_for_advanced_categories():
    for cat in ADVANCED_CLUTTER_CATEGORIES:
        assert legacy_to_advanced_override(cat) == cat


def test_simple_and_advanced_mappings_consistent():
    """Dual-mapping consistency: simple-mode and advanced-mode must agree.

    Every WorldCover class that maps to a legacy category with a direct
    advanced counterpart must produce the same result through both paths.
    """
    from clutter import CLUTTER_CATEGORIES, _WORLDCOVER_TO_CATEGORY
    from NoWires.clutter.grid import _WORLDCOVER_TO_ADVANCED_IDX, _ADVANCED_CATEGORIES
    consistent_legacy_classes = {10, 50, 60, 70, 80, 90}
    for cls_id in consistent_legacy_classes:
        legacy_cat = CLUTTER_CATEGORIES[_WORLDCOVER_TO_CATEGORY[cls_id]]
        advanced_cat = _ADVANCED_CATEGORIES[_WORLDCOVER_TO_ADVANCED_IDX[cls_id]]
        assert legacy_to_advanced_override(legacy_cat) == advanced_cat, (
            f"Class {cls_id}: legacy '{legacy_cat}' -> "
            f"'{legacy_to_advanced_override(legacy_cat)}' "
            f"but advanced mapping gives '{advanced_cat}'"
        )


def test_p2108_category_params_derived_from_clutter_categories():
    from clutter.p2108_height_gain import _CATEGORY_PARAMS
    for cat, params in _CATEGORY_PARAMS.items():
        assert cat in CLUTTER_CATEGORY_PARAMS, f"{cat} missing from CLUTTER_CATEGORY_PARAMS"
        assert params["R_m"] == CLUTTER_CATEGORY_PARAMS[cat]["R_m"], (
            f"{cat}: R_m mismatch"
        )
        assert params["method"] == CLUTTER_CATEGORY_PARAMS[cat]["p2108_3_1_method"], (
            f"{cat}: method mismatch"
        )