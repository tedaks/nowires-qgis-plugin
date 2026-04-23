# -*- coding: utf-8 -*-
"""Tests for reliability helpers."""

from reliability import (
    classify_fade_margin,
    estimate_formal_availability_pct,
    formal_availability_validity,
)


def test_formal_availability_validity_accepts_simple_los_case():
    result = formal_availability_validity(
        frequency_mhz=5800.0,
        distance_km=8.0,
        los_blocked=False,
    )
    assert result["valid"] is True
    assert result["method"] == "formal_p530"


def test_formal_availability_validity_rejects_blocked_case():
    result = formal_availability_validity(
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


def test_estimate_formal_availability_pct_stays_in_percent_range():
    value = estimate_formal_availability_pct(
        margin_db=20.0,
        distance_km=5.0,
        frequency_mhz=5800.0,
    )
    assert 0.0 <= value <= 100.0
