# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for reliability helpers."""

from reliability import (
    classify_fade_margin,
    estimate_heuristic_availability_pct,
    heuristic_availability_validity,
    summarize_reliability,
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
        frequency_mhz=5800.0,
        distance_km=12.0,
        los_blocked=True,
    )
    assert result["valid"] is False
    assert result["method"] == "fallback_margin"


def test_heuristic_availability_validity_accepts_sub_3ghz_unblocked():
    result = heuristic_availability_validity(
        frequency_mhz=900.0,
        distance_km=12.0,
        los_blocked=False,
    )
    assert result["valid"] is True
    assert result["method"] == "heuristic_availability"


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


class TestClassifyFadeMarginBoundaries:
    def test_strong_at_exact_boundary(self):
        result = classify_fade_margin(15.0)
        assert result["fade_margin_class"] == "Strong"

    def test_moderate_at_just_below_strong(self):
        result = classify_fade_margin(14.99)
        assert result["fade_margin_class"] == "Moderate"

    def test_moderate_at_exact_boundary(self):
        result = classify_fade_margin(5.0)
        assert result["fade_margin_class"] == "Moderate"

    def test_low_at_just_below_moderate(self):
        result = classify_fade_margin(4.99)
        assert result["fade_margin_class"] == "Low"

    def test_low_at_exact_boundary(self):
        result = classify_fade_margin(0.0)
        assert result["fade_margin_class"] == "Low"

    def test_weak_negative_margin(self):
        result = classify_fade_margin(-0.01)
        assert result["fade_margin_class"] == "Weak"
        assert result["reliability_summary"] == "Unreliable"

    def test_very_negative_margin(self):
        result = classify_fade_margin(-100.0)
        assert result["fade_margin_class"] == "Weak"


class TestEstimateHeuristicAvailabilityEdgeCases:
    def test_very_high_margin_approaches_100(self):
        value = estimate_heuristic_availability_pct(
            margin_db=200.0, distance_km=0.1, frequency_mhz=100.0,
        )
        assert value <= 100.0
        assert value > 90.0

    def test_very_negative_margin_floors_at_0(self):
        value = estimate_heuristic_availability_pct(
            margin_db=-200.0, distance_km=1000.0, frequency_mhz=50000.0,
        )
        assert value == 0.0

    def test_zero_distance_and_margin(self):
        value = estimate_heuristic_availability_pct(
            margin_db=0.0, distance_km=0.0, frequency_mhz=300.0,
        )
        assert 0.0 <= value <= 100.0


class TestHeuristicAvailabilityValidityEdgeCases:
    def test_zero_distance_is_invalid(self):
        result = heuristic_availability_validity(
            frequency_mhz=900.0, distance_km=0.0, los_blocked=False,
        )
        assert result["valid"] is False
        assert result["method"] == "fallback_margin"

    def test_zero_distance_blocked_is_also_invalid(self):
        result = heuristic_availability_validity(
            frequency_mhz=900.0, distance_km=0.0, los_blocked=True,
        )
        assert result["valid"] is False


class TestSummarizeReliability:
    def test_valid_unblocked_los_returns_availability(self):
        result = summarize_reliability(
            margin_db=10.0, frequency_mhz=900.0,
            distance_km=5.0, los_blocked=False,
        )
        assert result["availability_method"] == "heuristic_availability"
        assert result["availability_estimate_pct"] is not None
        assert result["fade_margin_class"] == "Moderate"
        assert result["reliability_summary"] == "Reliable"

    def test_blocked_los_uses_fallback_without_availability(self):
        result = summarize_reliability(
            margin_db=10.0, frequency_mhz=900.0,
            distance_km=5.0, los_blocked=True,
        )
        assert result["availability_method"] == "fallback_margin"
        assert result["availability_estimate_pct"] is None
        assert result["fade_margin_class"] == "Moderate"

    def test_weak_margin_blocked(self):
        result = summarize_reliability(
            margin_db=-5.0, frequency_mhz=5800.0,
            distance_km=10.0, los_blocked=True,
        )
        assert result["fade_margin_class"] == "Weak"
        assert result["availability_estimate_pct"] is None
