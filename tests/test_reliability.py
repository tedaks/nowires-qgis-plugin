# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for reliability helpers."""

from reliability import (
    classify_fade_margin,
    estimate_heuristic_availability_pct,
    heuristic_availability_validity,
)


def test_heuristic_availability_validity_accepts_simple_los_case():
    result = heuristic_availability_validity(
        frequency_mhz=5800.0,
        distance_km=8.0,
        los_blocked=False,
    )
    assert result["valid"] is True
    assert result["method"] == "heuristic_availability"


def test_heuristic_availability_validity_rejects_blocked_case():
    result = heuristic_availability_validity(
        frequency_mhz=900.0,
        distance_km=12.0,
        los_blocked=True,
    )
    assert result["valid"] is False
    assert result["method"] == "fallback_margin"


def test_classify_fade_margin_returns_reliable_for_strong_margin():
    result = classify_fade_margin(18.0)
    assert result["fade_margin_class"] == "Strong"
    assert result["reliability_summary"] == "Reliable"


def test_estimate_heuristic_availability_pct_stays_in_percent_range():
    value = estimate_heuristic_availability_pct(
        margin_db=20.0,
        distance_km=5.0,
        frequency_mhz=5800.0,
    )
    assert 0.0 <= value <= 100.0


def test_estimate_heuristic_availability_penalizes_higher_frequency():
    lower = estimate_heuristic_availability_pct(
        margin_db=10.0,
        distance_km=10.0,
        frequency_mhz=3000.0,
    )
    higher = estimate_heuristic_availability_pct(
        margin_db=10.0,
        distance_km=10.0,
        frequency_mhz=18000.0,
    )

    assert higher < lower
