# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression tests for zero-division guards in ITM propagation (bugs I7, N8)."""

import cmath
import math


from itm.propagation import knife_edge_diffraction, longley_rice


def test_knife_edge_diffraction_colocated_returns_zero():
    """I7: d_nlos==0 with d_hzn==[0,0] must return 0.0, not ZeroDivisionError."""
    # d_ML = 0+0 = 0, d_nlos = d__meter - d_ML = 0 when d__meter=0
    result = knife_edge_diffraction(
        d__meter=0.0,
        f__mhz=900.0,
        a_e__meter=8_500_000.0,
        theta_los=0.0,
        d_hzn__meter=[0.0, 0.0],
    )
    assert result == 0.0


def test_knife_edge_diffraction_d_nlos_negative_returns_zero():
    """I7: d_nlos<0 (LOS path) must return 0.0 without ZeroDivisionError."""
    d__meter = 500.0
    d_hzn = [300.0, 300.0]  # d_ML > d, so d_nlos < 0
    result = knife_edge_diffraction(
        d__meter=d__meter,
        f__mhz=900.0,
        a_e__meter=8_500_000.0,
        theta_los=0.0,
        d_hzn__meter=d_hzn,
    )
    assert result == 0.0


def test_knife_edge_diffraction_normal_path_still_works():
    """I7 guard must not change normal (non-zero d_nlos) computations."""
    a_e = 8_500_000.0
    h_e = [10.0, 10.0]
    d_hzn = [math.sqrt(2.0 * h_e[0] * a_e), math.sqrt(2.0 * h_e[1] * a_e)]
    d__meter = d_hzn[0] + d_hzn[1] + 1000.0
    theta_los = 0.0
    result = knife_edge_diffraction(
        d__meter=d__meter,
        f__mhz=900.0,
        a_e__meter=a_e,
        theta_los=theta_los,
        d_hzn__meter=d_hzn,
    )
    assert math.isfinite(result)
    assert result > 0.0


def _build_longley_rice_params_for_n8():
    """Construct params where d_sML ≈ d_0, triggering the N8 zero-division path.

    d_sML = sqrt(2*h_e[0]*a_e) + sqrt(2*h_e[1]*a_e)
    d_0   = 0.04 * f * h_e[0] * h_e[1]

    For equal h_e: set 2*sqrt(2*h*a_e) = 0.04*f*h^2 and solve for h.
    With f=900, a_e=8.5e6: h ≈ sqrt(2*sqrt(2*h*8.5e6)/(0.04*900)).
    We instead set h_e and f so d_sML == d_0 directly.
    """
    gamma_e = 1.0 / 8_500_000.0
    a_e = 1.0 / gamma_e
    h_e = [10.0, 10.0]
    f = 900.0

    d_hzn_s = [
        math.sqrt(2.0 * h_e[0] * a_e),
        math.sqrt(2.0 * h_e[1] * a_e),
    ]
    d_sML = d_hzn_s[0] + d_hzn_s[1]

    # d_0 = 0.04 * f * h_e[0] * h_e[1]
    d_0 = 0.04 * f * h_e[0] * h_e[1]

    # We need d_sML ≈ d_0. Choose h_e so these match.
    # For equal heights h: 2*sqrt(2*h*a_e) = 0.04*f*h^2
    # => h^(3/2) = 2*sqrt(2*a_e) / (0.04*f)
    # => h = (2*sqrt(2*a_e) / (0.04*f))^(2/3)
    target_h = (2.0 * math.sqrt(2.0 * a_e) / (0.04 * f)) ** (2.0 / 3.0)

    # Use target_h to set h_e, recompute
    h_e = [target_h, target_h]
    d_hzn_s = [
        math.sqrt(2.0 * h_e[0] * a_e),
        math.sqrt(2.0 * h_e[1] * a_e),
    ]
    d_sML = d_hzn_s[0] + d_hzn_s[1]
    d_0 = 0.04 * f * h_e[0] * h_e[1]

    # Verify d_sML ≈ d_0 (should be near-equal)
    assert abs(d_sML - d_0) / max(d_sML, d_0, 1.0) < 0.01

    # Set d_hzn = d_hzn_s (smooth earth = actual horizon)
    d_hzn = list(d_hzn_s)

    # d__meter must be < d_sML for LOS path
    d__meter = d_sML * 0.5

    # theta_hzn for smooth earth
    theta_hzn = [-d_hzn[i] / a_e for i in range(2)]

    # Z_g for vertical pol
    epsilon = 15.0
    sigma = 0.005
    ep_r = complex(epsilon, 18000.0 * sigma / f)
    Z_g = cmath.sqrt(ep_r - 1.0) / ep_r

    N_s = 301.0
    delta_h__meter = 0.0

    from itm._constants import MODE__P2P

    return dict(
        theta_hzn=theta_hzn,
        f__mhz=f,
        Z_g=Z_g,
        d_hzn__meter=d_hzn,
        h_e__meter=h_e,
        gamma_e=gamma_e,
        N_s=N_s,
        delta_h__meter=delta_h__meter,
        h__meter=(target_h, target_h),
        d__meter=d__meter,
        mode=MODE__P2P,
    )


def test_longley_rice_dsml_eq_d0_no_zero_div():
    """N8: d_sML ≈ d_0 must not raise ZeroDivisionError."""
    params = _build_longley_rice_params_for_n8()
    result = longley_rice(**params)
    A_ref, warnings, propmode = result
    assert math.isfinite(A_ref)


def test_longley_rice_dsml_eq_d0_finite_result():
    """N8: output must be a finite dB loss when d_sML ≈ d_0."""
    params = _build_longley_rice_params_for_n8()
    A_ref, warnings, propmode = longley_rice(**params)
    assert math.isfinite(A_ref)
    assert A_ref >= 0.0 or A_ref > -200.0  # sanity: not wildly negative


def test_knife_edge_diffraction_one_zero_horizon():
    """I7: d_nlos==0 when only one horizon is zero."""
    a_e = 8_500_000.0
    d_hzn = [0.0, math.sqrt(2.0 * 10.0 * a_e)]
    d_ML = d_hzn[0] + d_hzn[1]
    # d__meter == d_ML => d_nlos == 0
    result = knife_edge_diffraction(
        d__meter=d_ML,
        f__mhz=900.0,
        a_e__meter=a_e,
        theta_los=0.0,
        d_hzn__meter=d_hzn,
    )
    assert result == 0.0