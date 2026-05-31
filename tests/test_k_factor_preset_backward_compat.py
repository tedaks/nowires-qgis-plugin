# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test: the Decouple-N0 escape hatch restores the legacy behavior.

v2.0.0 couples each K_FACTOR_PRESET to a representative N0 by default. The
opt-in "Decouple N0 from k-factor preset" checkbox must restore the old
behavior: the preset affects only the Fresnel/LOS display and the user-entered
N0 is passed through unchanged.
"""

import os

from defaults import DEFAULT_N0
from radio import K_FACTOR_PRESETS, resolve_n0

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_decouple_passes_user_n0_through_for_every_preset():
    """With decouple on, the user's N0 is used regardless of preset."""
    user_n0 = 277.0
    for idx in range(len(K_FACTOR_PRESETS)):
        assert resolve_n0(preset_index=idx, decouple=True, user_n0=user_n0) == user_n0


def test_decouple_default_n0_unchanged():
    """Decouple on with the default N0 yields the default N0 (no override)."""
    assert resolve_n0(preset_index=4, decouple=True, user_n0=DEFAULT_N0) == DEFAULT_N0


def test_shared_params_registers_decouple_boolean():
    """add_advanced_itm_params registers a DECOUPLE_N0 boolean when k-factor is on."""
    src = _source("shared_params.py")
    assert "DECOUPLE_N0" in src
    assert "QgsProcessingParameterBoolean" in src


def test_p2p_algorithm_reads_decouple_and_resolves_n0():
    """P2P wires the checkbox through resolve_n0."""
    src = _source("algorithm/p2p.py")
    assert "DECOUPLE_N0" in src
    assert "resolve_n0(" in src


def test_batch_algorithm_reads_decouple_and_resolves_n0():
    """Batch wires the checkbox through resolve_n0."""
    src = _source("algorithm/batch.py")
    assert "DECOUPLE_N0" in src
    assert "resolve_n0(" in src
