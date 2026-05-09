import logging

from .clutter_categories import (
    CLUTTER_CATEGORY_PARAMS,
    worldcover_class_to_advanced_category,
)
from .p2108_height_gain import height_gain_loss
from .p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat
from .p2109_bel import building_entry_loss
from .clutter_saalos import clutter_loss_saalos

logger = logging.getLogger(__name__)


def _category_height_m(category, override_m):
    if override_m is not None and override_m > 0.0:
        return float(override_m)
    params = CLUTTER_CATEGORY_PARAMS.get(category, CLUTTER_CATEGORY_PARAMS["open"])
    return float(params["height_m"])


def _terminal_height_m(terminal, context):
    return context.tx_height_m if terminal == "tx" else context.rx_height_m


def _compute_advanced_loss(category, terminal, context):
    """Compute per-terminal clutter loss using the §6 dispatch table."""
    params = CLUTTER_CATEGORY_PARAMS.get(category, CLUTTER_CATEGORY_PARAMS["open"])
    model = params["model"]
    cch_m = _category_height_m(category, context.cch_override_m)
    ant_h_m = _terminal_height_m(terminal, context)
    if model == "none" or cch_m <= 0.0:
        return 0.0, "none"
    if ant_h_m >= cch_m:
        return 0.0, model
    f_ghz = context.frequency_mhz / 1000.0
    d_km = context.distance_m / 1000.0
    p = context.percentile
    s32_applicable = params.get("p2108_3_2_applicable", False)
    if model == "saalos":
        loss = clutter_loss_saalos(
            d__meter=context.distance_m,
            cch__meter=cch_m,
            h_tx__meter=cch_m,
            h_rx__meter=ant_h_m,
            h_rx_gnd__meter=context.rx_ground_elevation_m,
            pol=context.polarization,
            f__mhz=context.frequency_mhz,
        )
        return loss, "saalos"
    if model == "p2108_height_gain":
        loss_hg = height_gain_loss(
            ant_h_m, f_ghz, category,
            w_s_m=context.street_width_m,
        )
        return loss_hg, "p2108_height_gain"
    if model == "p2108_combined":
        hg_loss = 0.0
        stat_loss = 0.0
        method_parts = []
        if f_ghz < 0.5:
            pass
        elif f_ghz <= 3.0:
            hg_loss = height_gain_loss(
                ant_h_m, f_ghz, category,
                w_s_m=context.street_width_m,
            )
            if hg_loss > 0.0:
                method_parts.append("§3.1")
            if s32_applicable:
                stat_loss = clutter_loss_p2108_terrestrial_stat(
                    d_km, f_ghz, p=p,
                )
                if stat_loss > 0.0:
                    method_parts.append("§3.2")
        elif f_ghz <= 67.0:
            if s32_applicable:
                stat_loss = clutter_loss_p2108_terrestrial_stat(
                    d_km, f_ghz, p=p,
                )
                if stat_loss > 0.0:
                    method_parts.append("§3.2")
        else:
            if s32_applicable:
                stat_loss = clutter_loss_p2108_terrestrial_stat(
                    d_km, 67.0, p=p,
                )
                if stat_loss > 0.0:
                    method_parts.append("§3.2(clamped)")
        combined = max(hg_loss, stat_loss) if method_parts else 0.0
        method_str = "+".join(method_parts) if method_parts else "p2108_combined(0)"
        return combined, method_str
    return 0.0, "unknown"


def compute_terminal_clutter_loss(category, terminal, context):
    """Compute per-terminal clutter loss (advanced or simple model)."""
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
    if model in ("p2108_height_gain", "p2108_combined"):
        loss, _method = _compute_advanced_loss(category, terminal, context)
        return loss
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


def _resolve_category(lat, lon, override, land_cover_grid):
    if override:
        return override, "override"
    if land_cover_grid is not None:
        category = land_cover_grid.sample_category(lat, lon)
        if category is not None:
            return category, land_cover_grid.source
    return "open", "fallback_open"


def compute_terminal_clutter_losses(
    tx_lat, tx_lon, rx_lat, rx_lon, frequency_mhz,
    enabled=False, land_cover_grid=None, tx_override=None, rx_override=None,
    context=None,
):
    from .clutter import clutter_loss_db, TerminalClutterLosses
    if not enabled:
        return TerminalClutterLosses("open", "open", 0.0, 0.0, 0.0, "off")
    advanced = context is not None and context.model in ("advanced", "p2108_combined")
    if not advanced:
        tx_cat, tx_src = _resolve_category(tx_lat, tx_lon, tx_override, land_cover_grid)
        rx_cat, rx_src = _resolve_category(rx_lat, rx_lon, rx_override, land_cover_grid)
        tx_loss = clutter_loss_db(tx_cat, frequency_mhz)
        rx_loss = clutter_loss_db(rx_cat, frequency_mhz)
        source = tx_src if tx_src == rx_src else "{},{}".format(tx_src, rx_src)
        return TerminalClutterLosses(tx_cat, rx_cat, tx_loss, rx_loss, tx_loss + rx_loss, source)
    tx_cat, tx_src = _resolve_category_advanced(tx_lat, tx_lon, tx_override, land_cover_grid)
    rx_cat, rx_src = _resolve_category_advanced(rx_lat, rx_lon, rx_override, land_cover_grid)
    tx_loss, tx_method = _compute_advanced_loss(tx_cat, "tx", context)
    rx_loss, rx_method = _compute_advanced_loss(rx_cat, "rx", context)
    tx_cch = _category_height_m(tx_cat, context.cch_override_m)
    rx_cch = _category_height_m(rx_cat, context.cch_override_m)
    source = tx_src if tx_src == rx_src else "{},{}".format(tx_src, rx_src)
    method = "{}/{}".format(tx_method, rx_method)
    total = tx_loss + rx_loss
    rx_bel = 0.0
    if context.bel_enabled:
        f_ghz = frequency_mhz / 1000.0
        rx_bel = building_entry_loss(
            f_ghz, context.bel_building_type,
            theta_deg=context.bel_elevation_angle_deg,
            p=context.percentile,
        )
    total_with_bel = total + rx_bel
    return TerminalClutterLosses(
        tx_category=tx_cat, rx_category=rx_cat,
        tx_loss_db=tx_loss, rx_loss_db=rx_loss,
        total_loss_db=total, source=source,
        tx_cch_m=tx_cch, rx_cch_m=rx_cch,
        tx_bel_db=0.0, rx_bel_db=rx_bel,
        total_with_bel_db=total_with_bel,
        method=method, percentile=context.percentile,
    )