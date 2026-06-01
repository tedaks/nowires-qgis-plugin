# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Reference smoke tests for bundled ITM primitives."""

import math

import numpy as np
import pytest

from itm import Climate, Polarization, TerrainProfile, predict_p2p
from itm.propagation import free_space_loss, fresnel_integral, h0_function
from itm.terrain import compute_delta_h


def test_free_space_loss_matches_known_1km_1ghz_value():
    assert free_space_loss(1000.0, 1000.0) == pytest.approx(92.45)


def test_fresnel_integral_low_and_high_branches_are_finite():
    assert fresnel_integral(1.0) == pytest.approx(13.86)
    assert fresnel_integral(9.0) == pytest.approx(12.953 + 10.0 * math.log10(9.0))


def test_h0_function_clamps_eta_and_returns_finite_value():
    low_eta = h0_function(10.0, 0.1)
    high_eta = h0_function(10.0, 9.0)

    assert math.isfinite(low_eta)
    assert math.isfinite(high_eta)
    assert low_eta == pytest.approx(h0_function(10.0, 1.0))
    assert high_eta == pytest.approx(h0_function(10.0, 5.0))


def test_compute_delta_h_is_zero_for_flat_terrain():
    elevations = np.full(101, 100.0, dtype=float)
    assert compute_delta_h(elevations, 30.0, 0.0, 3000.0) == pytest.approx(0.0)


def test_predict_p2p_returns_finite_loss_and_intermediate_values():
    terrain = TerrainProfile(
        elevations=np.linspace(100.0, 105.0, 51, dtype=float),
        resolution=30.0,
    )

    result = predict_p2p(
        h_tx__meter=30.0,
        h_rx__meter=10.0,
        terrain=terrain,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0,
        f__mhz=5800.0,
        pol=Polarization.VERTICAL,
        epsilon=15.0,
        sigma=0.005,
        mdvar=0,
        time=50.0,
        location=50.0,
        situation=50.0,
        return_intermediate=True,
    )

    assert math.isfinite(result.A__db)
    assert result.A__db > 0.0
    assert result.intermediate is not None
    assert result.intermediate.d__km == pytest.approx(1.5)
