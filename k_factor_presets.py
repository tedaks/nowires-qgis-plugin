# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Earth-radius factor (k) presets and their coupling to surface refractivity.

Split out of ``radio.py`` to keep that module under the 300-line gate. These
symbols are re-exported from ``radio`` for backward compatibility, so existing
``from NoWires.radio import K_FACTOR_PRESETS, resolve_k_factor`` imports keep
working.
"""

import logging

from NoWires.defaults import DEFAULT_K_FACTOR, DEFAULT_N0

logger = logging.getLogger(__name__)

# Earth-radius factor (k) presets exposed by the P2P/Batch algorithm UI.
# Index 2 (4/3) is the standard-atmosphere default.
K_FACTOR_PRESETS = [0.67, 1.0, DEFAULT_K_FACTOR, 2.0, 4.0]

# Representative surface refractivity N0 (N-units) coupled to each k-factor
# preset (v2.0.0). Sub-refractive -> low N0, super-refractive -> high N0,
# spanning the valid [ITM_MIN_N0, ITM_MAX_N0] band. Index 2 (standard
# atmosphere, k = 4/3) is pinned to DEFAULT_N0 so the out-of-box default is
# unchanged; the sub-/super-refractive ends are representative planning values
# (Bean-Dutton saturates past 400 N-units and is undefined for k < 1).
K_FACTOR_PRESET_N0 = [250.0, 280.0, DEFAULT_N0, 350.0, 400.0]


def resolve_k_factor(
    has_preset: bool, has_custom: bool, custom_value: float | None,
    preset_index: int, presets: list[float] = K_FACTOR_PRESETS,
) -> float:
    """Pick the effective Earth-radius factor (k) for a P2P run.

    Prefers the preset enum; falls back to the legacy numeric K_FACTOR only
    when the preset is absent and the custom value was supplied.
    """
    if has_preset and has_custom:
        logger.warning(
            "K_FACTOR preset selected; custom K_FACTOR=%s is ignored, "
            "using preset index %s instead.",
            custom_value, preset_index,
        )
    if not has_preset and has_custom:
        assert custom_value is not None
        return float(custom_value)
    return presets[preset_index]


def resolve_n0(
    preset_index: int, decouple: bool, user_n0: float,
    presets_n0: list[float] = K_FACTOR_PRESET_N0,
) -> float:
    """Pick the effective surface refractivity N0 for a P2P/Batch run.

    By default (v2.0.0) the k-factor preset is coupled to a representative N0:
    selecting a real preset overrides the user-entered N0. The coupling is
    skipped — the user's N0 is used unchanged — when either:

    * ``decouple`` is True (the opt-in "Decouple N0 from k-factor preset"
      checkbox, restoring the pre-v2.0.0 behavior where the preset affected
      only the Fresnel/LOS display), or
    * ``preset_index`` is the Custom entry (>= ``len(presets_n0)``), which
      already leaves k — and now N0 — under direct user control.
    """
    if decouple or preset_index >= len(presets_n0):
        return float(user_n0)
    return presets_n0[preset_index]
