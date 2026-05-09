import pytest
from clutter_categories import (
    ADVANCED_CLUTTER_CATEGORIES,
    CLUTTER_CATEGORY_PARAMS,
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
            "none", "saalos", "p2108_height_gain", "p2108_combined",
        )


def test_category_model_assignments():
    assert CLUTTER_CATEGORY_PARAMS["vegetation"]["model"] == "saalos"
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