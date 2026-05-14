# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import logging
from dataclasses import dataclass

from .clutter_categories import (
    CLUTTER_CATEGORY_PARAMS,
    legacy_to_advanced_override,
    worldcover_class_to_advanced_category,
)
from .p2108_height_gain import height_gain_loss
from .p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat
from .p2109_bel import building_entry_loss
from .clutter_saalos import clutter_loss_saalos

logger = logging.getLogger(__name__)

# P.2108-1 §3.2 statistical clutter loss validity lower bound (GHz).
# Below this, p2108_combined categories (suburban/urban) silently contribute
# zero clutter loss in advanced mode. We log a one-shot warning so users
# aren't surprised when built-environment areas show free-space-equivalent
# coverage at low VHF.
_P2108_S32_MIN_GHZ = 0.5
_warned_low_vhf_p2108_combined = False


def _maybe_warn_low_vhf_p2108_combined(f_ghz, category):
    """Emit a one-shot warning when p2108_combined silently returns zero."""
    global _warned_low_vhf_p2108_combined
    if _warned_low_vhf_p2108_combined:
        return
    _warned_low_vhf_p2108_combined = True
    logger.warning(
        "P.2108 §3.2 invalid below %.1f GHz; advanced clutter for category "
        "%s at %.3f GHz contributes 0 dB. Consider 'simple' mode for "
        "built-environment loss at low VHF.",
        _P2108_S32_MIN_GHZ, category, f_ghz,
    )


@dataclass(frozen=True)
class _ClutterComponents:
    """Decomposed clutter loss: per-terminal and per-path components.

    terminal_loss_db: per-terminal loss (§3.1 height-gain for p2108_combined).
    path_loss_db: per-path loss (§3.2 statistical; 0 for per-terminal models).
    model: model identifier string for reporting.
    """
    terminal_loss_db: float = 0.0
    path_loss_db: float = 0.0
    model: str = "none"


def _category_height_m(category, override_m):
    if override_m is not None and override_m > 0.0:
        return float(override_m)
    params = CLUTTER_CATEGORY_PARAMS.get(category, CLUTTER_CATEGORY_PARAMS["open"])
    return float(params["height_m"])


def _terminal_height_m(terminal, context):
    return context.tx_height_m if terminal == "tx" else context.rx_height_m


def _terminal_ground_elev_m(terminal, context):
    return context.tx_ground_elevation_m if terminal == "tx" else context.rx_ground_elevation_m


def _compute_advanced_loss(category, terminal, context):
    """Compute per-terminal clutter loss split into terminal and path parts.

    §3.1 height-gain is per-terminal; §3.2 statistical clutter loss is
    per-path. Returning them separately avoids double-counting when both
    endpoints compute stat_loss independently.
    """
    params = CLUTTER_CATEGORY_PARAMS.get(category, CLUTTER_CATEGORY_PARAMS["open"])
    model = params["model"]
    cch_m = _category_height_m(category, context.cch_override_m)
    ant_h_m = _terminal_height_m(terminal, context)
    if model == "none" or cch_m <= 0.0:
        return _ClutterComponents(0.0, 0.0, "none")
    if ant_h_m >= cch_m:
        return _ClutterComponents(0.0, 0.0, model)
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
            h_rx_gnd__meter=_terminal_ground_elev_m(terminal, context),
            pol=context.polarization,
            f__mhz=context.frequency_mhz,
        )
        return _ClutterComponents(loss, 0.0, "saalos")
    if model == "p2108_height_gain":
        loss_hg = height_gain_loss(
            ant_h_m, f_ghz, category,
            w_s_m=context.street_width_m,
        )
        return _ClutterComponents(loss_hg, 0.0, "p2108_height_gain")
    if model == "p2108_combined":
        hg_loss = 0.0
        stat_loss = 0.0
        method_parts = []
        if f_ghz < _P2108_S32_MIN_GHZ:
            _maybe_warn_low_vhf_p2108_combined(f_ghz, category)
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
        # §3.1 (height-gain) is per-terminal; §3.2 (statistical) is per-path.
        # Return them separately so the caller can combine correctly across
        # both endpoints without double-counting the path component.
        method_str = "+".join(method_parts) if method_parts else "p2108_combined(0)"
        return _ClutterComponents(hg_loss, stat_loss, method_str)
    return _ClutterComponents(0.0, 0.0, "unknown")


def compute_terminal_clutter_loss(category, terminal, context):
    """Per-terminal clutter loss for per-pixel LUT use.

    Returns only the terminal-level contribution (§3.1 height-gain for
    p2108_combined). Path-level §3.2 must be combined at the path level
    via compute_path_clutter_loss().
    """
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
            h_rx_gnd__meter=_terminal_ground_elev_m(terminal, context),
            pol=context.polarization,
            f__mhz=context.frequency_mhz,
        )
    if model in ("p2108_height_gain", "p2108_combined"):
        comp = _compute_advanced_loss(category, terminal, context)
        return comp.terminal_loss_db
    return 0.0


def compute_path_clutter_loss(tx_comp, rx_comp):
    """Combine per-terminal clutter components into path loss (dB).

    §3.2 stat_loss is per-path, applied once via max(hg_tx+hg_rx, stat_loss).
    SAALOS on both endpoints: take max rather than sum. p2108_height_gain:
    additive across endpoints.
    """
    tx_model = tx_comp.model
    rx_model = rx_comp.model
    tx_path = tx_comp.path_loss_db
    tx_term = tx_comp.terminal_loss_db
    rx_term = rx_comp.terminal_loss_db
    rx_path = rx_comp.path_loss_db
    if tx_model == "none" and rx_model == "none":
        return 0.0
    hg_total = tx_term + rx_term
    # §3.2 is a path statistic; take max rather than sum because both
    # endpoints compute the same quantity from the same path parameters.
    path_stat = max(tx_path, rx_path)
    if tx_model == "saalos" and rx_model == "saalos":
        return max(tx_term, rx_term)
    if "saalos" in (tx_model, rx_model):
        saalos_term = tx_term if tx_model == "saalos" else rx_term
        other_term = rx_term if tx_model == "saalos" else tx_term
        other_path = rx_path if tx_model == "saalos" else tx_path
        return max(saalos_term + other_term, other_path)
    if path_stat > 0.0:
        return max(hg_total, path_stat)
    return hg_total


def _legacy_to_advanced_override(name):
    return legacy_to_advanced_override(name)


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
    advanced = context is not None and context.model == "advanced"
    if not advanced:
        tx_cat, tx_src = _resolve_category(tx_lat, tx_lon, tx_override, land_cover_grid)
        rx_cat, rx_src = _resolve_category(rx_lat, rx_lon, rx_override, land_cover_grid)
        tx_loss = clutter_loss_db(tx_cat, frequency_mhz)
        rx_loss = clutter_loss_db(rx_cat, frequency_mhz)
        source = tx_src if tx_src == rx_src else "{},{}".format(tx_src, rx_src)
        return TerminalClutterLosses(tx_cat, rx_cat, tx_loss, rx_loss, tx_loss + rx_loss, source)
    tx_cat, tx_src = _resolve_category_advanced(tx_lat, tx_lon, tx_override, land_cover_grid)
    rx_cat, rx_src = _resolve_category_advanced(rx_lat, rx_lon, rx_override, land_cover_grid)
    tx_comp = _compute_advanced_loss(tx_cat, "tx", context)
    rx_comp = _compute_advanced_loss(rx_cat, "rx", context)
    tx_cch = _category_height_m(tx_cat, context.cch_override_m)
    rx_cch = _category_height_m(rx_cat, context.cch_override_m)
    source = tx_src if tx_src == rx_src else "{},{}".format(tx_src, rx_src)
    method = "{}/{}".format(tx_comp.model, rx_comp.model)
    total = compute_path_clutter_loss(tx_comp, rx_comp)
    # Assign per-terminal losses for reporting so that
    # tx_loss + rx_loss == total holds in every case. For path-level
    # components (both-saalos, or §3.2 dominance) split the residual onto
    # the dominant terminal; per-terminal-only models (§3.1 hg) split
    # naturally from terminal_loss_db.
    term_sum = tx_comp.terminal_loss_db + rx_comp.terminal_loss_db
    both_saalos = (tx_comp.model == "saalos" and rx_comp.model == "saalos")
    if both_saalos:
        if tx_comp.terminal_loss_db >= rx_comp.terminal_loss_db:
            tx_loss = total
            rx_loss = 0.0
        else:
            tx_loss = 0.0
            rx_loss = total
    elif term_sum > 0.0:
        # Proportional split preserves the invariant even when path_stat
        # dominates (total > term_sum) — extra dB lands on each terminal
        # in proportion to its per-terminal contribution.
        tx_loss = total * (tx_comp.terminal_loss_db / term_sum)
        rx_loss = total * (rx_comp.terminal_loss_db / term_sum)
    else:
        # No per-terminal contribution: hand the whole path stat to RX so
        # the dominant carrier of path-level clutter remains identifiable.
        tx_loss = 0.0
        rx_loss = total
    # Design decision: BEL (P.2109-2) is additive with P.2108 clutter loss
    # because §3.1/§3.2 model terminal-local multipath/scatter effects while
    # P.2109 models building penetration — different physical mechanisms that
    # both contribute independent losses for an outdoor-to-indoor link.
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