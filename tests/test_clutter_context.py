# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
from types import SimpleNamespace

from clutter.context import (
    ClutterLossContext,
    build_initial_clutter_context,
    build_link_clutter_context,
)


def test_defaults_to_simple_model():
    ctx = ClutterLossContext(
        frequency_mhz=900.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0,
    )
    assert ctx.model == "simple"
    assert ctx.cch_override_m is None
    assert ctx.percentile == 50.0
    assert ctx.street_width_m == 27.0
    assert ctx.bel_enabled is False
    assert ctx.bel_building_type == "traditional"
    assert ctx.bel_elevation_angle_deg == 0.0


def test_advanced_with_overrides():
    ctx = ClutterLossContext(
        frequency_mhz=1800.0, distance_m=2500.0,
        tx_height_m=25.0, rx_height_m=1.5,
        cch_override_m=18.0, model="advanced",
    )
    assert ctx.model == "advanced"
    assert ctx.cch_override_m == 18.0


def test_advanced_with_bel_params():
    ctx = ClutterLossContext(
        frequency_mhz=3500.0, distance_m=1000.0,
        tx_height_m=25.0, rx_height_m=2.0,
        model="advanced", percentile=90.0,
        street_width_m=20.0, bel_enabled=True,
        bel_building_type="thermally_efficient",
        bel_elevation_angle_deg=15.0,
    )
    assert ctx.percentile == 90.0
    assert ctx.street_width_m == 20.0
    assert ctx.bel_enabled is True
    assert ctx.bel_building_type == "thermally_efficient"
    assert ctx.bel_elevation_angle_deg == 15.0


def _stub_params():
    """Minimal duck-typed params for build_link_clutter_context.

    Mirrors the fields the factory reads from a P2PAnalysisParams /
    BatchAnalysisParams object. Update this stub if those classes grow
    new clutter fields.
    """
    return SimpleNamespace(
        f_mhz=2400.0,
        cch_override_m=15.0, clutter_model="advanced",
        clutter_percentile=95.0, street_width_m=30.0,
        bel_enabled=True, bel_building_type="thermally_efficient",
        bel_elevation_angle_deg=10.0,
    )


def test_build_link_clutter_context_maps_all_fields():
    ctx = build_link_clutter_context(
        params=_stub_params(), dist_m=5000.0,
        tx_h=40.0, rx_h=2.5,
    )
    assert ctx.distance_m == 5000.0
    assert ctx.tx_height_m == 40.0
    assert ctx.rx_height_m == 2.5
    assert ctx.frequency_mhz == 2400.0
    assert ctx.cch_override_m == 15.0
    assert ctx.model == "advanced"
    assert ctx.percentile == 95.0
    assert ctx.street_width_m == 30.0
    assert ctx.bel_enabled is True
    assert ctx.bel_building_type == "thermally_efficient"
    assert ctx.bel_elevation_angle_deg == 10.0


def test_build_link_clutter_context_distance_independent_of_params():
    ctx = build_link_clutter_context(
        params=_stub_params(), dist_m=0.5,
        tx_h=10.0, rx_h=1.0,
    )
    assert ctx.distance_m == 0.5


def test_build_link_clutter_context_overrides_params_tx_rx_h():
    params = SimpleNamespace(
        f_mhz=900.0,
        cch_override_m=None, clutter_model="simple",
        clutter_percentile=50.0, street_width_m=27.0,
        bel_enabled=False, bel_building_type="traditional",
        bel_elevation_angle_deg=0.0,
    )
    ctx = build_link_clutter_context(
        params=params, dist_m=1000.0,
        tx_h=99.0, rx_h=1.5,
    )
    assert ctx.tx_height_m == 99.0
    assert ctx.rx_height_m == 1.5


def test_build_initial_clutter_context_placeholder_semantics():
    ctx = build_initial_clutter_context(
        frequency_mhz=900.0, tx_height_m=30.0, rx_height_m=2.0,
        cch_override_m=None, model="simple", percentile=50.0,
        street_width_m=27.0, bel_enabled=False,
        bel_building_type="traditional", bel_elevation_angle_deg=0.0,
    )
    assert ctx.distance_m == 0.0