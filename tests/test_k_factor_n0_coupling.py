# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test: K_FACTOR_PRESET is coupled to a representative N0 value.

v2.0.0 default change. Each non-Custom K_FACTOR_PRESET now maps to a
representative surface-refractivity N0 (sub-refractive -> low N0,
super-refractive -> high N0) so that selecting a preset changes the ITM
propagation prediction, not only the Fresnel/LOS display geometry.

The standard-atmosphere preset (index 2, k = 4/3) must map to DEFAULT_N0 so
the out-of-box default behavior is unchanged.
"""

from defaults import DEFAULT_N0
from radio import K_FACTOR_PRESETS, K_FACTOR_PRESET_N0, itm_p2p_loss, resolve_n0

# Full-range spread chosen for v2.0.0 (valid N0 band is 250-400 N-units).
EXPECTED_N0_BY_PRESET = [250.0, 280.0, 301.0, 350.0, 400.0]


def test_mapping_has_one_n0_per_k_factor_preset():
    """Every k-factor preset has a coupled N0; no orphans."""
    assert len(K_FACTOR_PRESET_N0) == len(K_FACTOR_PRESETS)


def test_mapping_values_are_the_full_range_spread():
    """The coupled N0 values match the agreed full-range spread."""
    assert list(K_FACTOR_PRESET_N0) == EXPECTED_N0_BY_PRESET


def test_mapping_is_monotonic_with_k():
    """Higher k (more super-refractive) maps to higher N0."""
    assert K_FACTOR_PRESET_N0 == sorted(K_FACTOR_PRESET_N0)


def test_standard_preset_maps_to_default_n0():
    """k = 4/3 (index 2, standard atmosphere) preserves the current default."""
    standard_index = K_FACTOR_PRESETS.index(4.0 / 3.0)
    assert standard_index == 2
    assert K_FACTOR_PRESET_N0[standard_index] == DEFAULT_N0


def test_resolve_n0_returns_coupled_value_for_each_preset():
    """With coupling active, resolve_n0 ignores the user N0 for real presets."""
    bogus_user_n0 = 333.0
    for idx, expected in enumerate(EXPECTED_N0_BY_PRESET):
        got = resolve_n0(preset_index=idx, decouple=False, user_n0=bogus_user_n0)
        assert got == expected, "preset {} should couple to {}".format(idx, expected)


def test_resolve_n0_custom_preset_uses_user_value():
    """The Custom preset (index == len(presets)) leaves N0 under user control."""
    custom_index = len(K_FACTOR_PRESETS)  # 5
    assert resolve_n0(preset_index=custom_index, decouple=False, user_n0=275.0) == 275.0


def test_coupled_n0_changes_itm_propagation_loss():
    """Selecting a different preset must change the predicted basic loss.

    Runs the bundled ITM model with the coupled N0 for the sub-refractive and
    strong super-refractive presets and asserts the loss differs.
    """
    # 49-sample PFL: [n_intervals, interval_m, elevations...].
    elevations = [
        100.0, 120.0, 90.0, 110.0, 80.0, 130.0, 100.0, 95.0, 105.0, 100.0,
        98.0, 102.0, 99.0, 101.0, 100.0, 100.0, 90.0, 100.0, 100.0, 100.0,
        100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
        100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
        100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
    ]
    profile = [float(len(elevations) - 1), 50.0, *elevations]

    sub = resolve_n0(preset_index=0, decouple=False, user_n0=DEFAULT_N0)
    sup = resolve_n0(preset_index=4, decouple=False, user_n0=DEFAULT_N0)

    loss_sub = itm_p2p_loss(30.0, 10.0, profile, climate=1, N0=sub, f__mhz=900.0)
    loss_sup = itm_p2p_loss(30.0, 10.0, profile, climate=1, N0=sup, f__mhz=900.0)

    assert not loss_sub.failed and not loss_sup.failed
    assert loss_sub.loss_db != loss_sup.loss_db, (
        "Coupled N0 (sub-refractive {} vs super-refractive {}) must change "
        "the ITM propagation loss".format(sub, sup)
    )
