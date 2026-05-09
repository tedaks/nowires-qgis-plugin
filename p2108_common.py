# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

"""Shared helpers for ITU-R P.2108-1 and P.2109-2 implementations.

P.2108 uses Q^-1 (inverse complementary normal CDF):
    Q^-1(alpha) = -F^-1(alpha)
where F^-1 is the standard inverse normal CDF.

P.2109 uses F^-1 (regular inverse normal CDF).
"""

import math

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)


def _ndtr(x):
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _ndtri(p):
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")
    if p <= 0.5:
        q = p
    else:
        q = 1.0 - p
    t = math.sqrt(-2.0 * math.log(q))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    x_abs = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)
    if p <= 0.5:
        x = -x_abs
    else:
        x = x_abs
    for _ in range(2):
        cdf = 0.5 * (1.0 + math.erf(x / _SQRT2))
        pdf = math.exp(-0.5 * x * x) / _SQRT2PI
        x -= (cdf - p) / pdf
    return x


def q_inv_complementary_normal(p_pct):
    """Q^-1(p_pct/100): inverse complementary normal CDF (P.2108 convention).

    Q^-1(alpha) = -F^-1(alpha).
    At p=50, Q^-1(0.5) = 0. As p increases toward 100,
    Q^-1 -> -infinity (more loss not exceeded for higher percentiles).
    """
    alpha = p_pct / 100.0
    alpha = max(1e-12, min(alpha, 1.0 - 1e-12))
    return -_ndtri(alpha)


def f_inv_normal(p_pct):
    """F^-1(p_pct/100): regular inverse normal CDF (P.2109 convention).

    At p=50, F^-1(0.5) = 0. As p increases toward 100,
    F^-1 -> +infinity (more loss for higher probability).
    """
    alpha = p_pct / 100.0
    alpha = max(1e-12, min(alpha, 1.0 - 1e-12))
    return _ndtri(alpha)


def validate_frequency_ghz(f_ghz, min_ghz, max_ghz, name="frequency"):
    """Clamp frequency to valid range and return (f_clamped, was_clamped)."""
    if f_ghz < min_ghz:
        return min_ghz, True
    if f_ghz > max_ghz:
        return max_ghz, True
    return f_ghz, False


def validate_distance_km(d_km, min_km=None, name="distance"):
    """Clamp distance to valid range and return (d_clamped, was_clamped)."""
    if min_km is not None and d_km < min_km:
        return min_km, True
    return d_km, False