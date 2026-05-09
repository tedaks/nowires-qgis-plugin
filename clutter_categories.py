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

_WORLDVER_MAP = {
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
        return _WORLDVER_MAP.get(int(class_id), "open")
    except (TypeError, ValueError):
        return "open"