from .clutter_categories import (
    ADVANCED_CLUTTER_CATEGORIES,
    CLUTTER_CATEGORY_PARAMS,
    worldcover_class_to_advanced_category,
)
from .clutter_constants import MAX_CLUTTER_LOSS
from .clutter_context import ClutterLossContext
from .clutter_p2108 import clutter_loss_p2108
from .clutter_saalos import clutter_loss_saalos


def _category_height_m(category, override_m):
    if override_m is not None and override_m > 0.0:
        return float(override_m)
    params = CLUTTER_CATEGORY_PARAMS.get(category, CLUTTER_CATEGORY_PARAMS["open"])
    return float(params["height_m"])


def _terminal_height_m(terminal, context):
    return context.tx_height_m if terminal == "tx" else context.rx_height_m


def compute_terminal_clutter_loss(category, terminal, context):
    params = CLUTTER_CATEGORY_PARAMS.get(category, CLUTTER_CATEGORY_PARAMS["open"])
    model = params["model"]
    cch_m = _category_height_m(category, context.cch_override_m)
    ant_h_m = _terminal_height_m(terminal, context)
    if model == "none" or cch_m <= 0.0:
        return 0.0
    if ant_h_m >= cch_m:
        return 0.0
    if context.distance_m <= 0.0:
        return 0.0
    if model == "saalos":
        return clutter_loss_saalos(
            d__meter=context.distance_m,
            cch__meter=cch_m,
            h_tx__meter=cch_m,
            h_rx__meter=ant_h_m,
            h_rx_gnd__meter=context.rx_ground_elevation_m,
            pol=context.polarization,
            f__mhz=context.frequency_mhz,
        )
    if model == "p2108":
        return clutter_loss_p2108(context.distance_m, category, context.frequency_mhz)
    return 0.0


_LEGACY_TO_ADVANCED = {
    "open": "open",
    "rural": "open_rural",
    "vegetation": "vegetation",
    "suburban": "suburban",
    "urban": "urban",
    "open_rural": "open_rural",
    "dense_rural": "dense_rural",
}


def _legacy_to_advanced_override(name):
    return _LEGACY_TO_ADVANCED.get(name, "open")


def _resolve_category_advanced(lat, lon, override, land_cover_grid):
    if override:
        return _legacy_to_advanced_override(override), "override"
    if land_cover_grid is not None:
        class_id = land_cover_grid.sample_class(lat, lon)
        if class_id is not None:
            return worldcover_class_to_advanced_category(class_id), land_cover_grid.source
    return "open", "fallback_open"