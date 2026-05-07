ADVANCED_CLUTTER_CATEGORIES = (
    "open",
    "open_rural",
    "dense_rural",
    "vegetation",
    "suburban",
    "urban",
)

CLUTTER_CATEGORY_PARAMS = {
    "open":        {"height_m": 0.0,  "model": "none",   "base_loss_db": 0.0,  "description": "Water, bare ground, snow/ice, wetland"},
    "open_rural":  {"height_m": 2.0,  "model": "p2108",  "base_loss_db": 2.0,  "description": "Grassland, cropland"},
    "dense_rural": {"height_m": 4.0,  "model": "p2108",  "base_loss_db": 4.0,  "description": "Shrubland, moss/lichen"},
    "vegetation":  {"height_m": 12.0, "model": "saalos", "base_loss_db": 6.0,  "description": "Tree cover, mangroves"},
    "suburban":    {"height_m": 9.0,  "model": "p2108",  "base_loss_db": 8.0,  "description": "Low-density built-up"},
    "urban":       {"height_m": 15.0, "model": "p2108",  "base_loss_db": 10.0, "description": "High-density built-up"},
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