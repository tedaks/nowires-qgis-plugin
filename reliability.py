# -*- coding: utf-8 -*-
"""Pure-Python helpers for NoWires reliability outputs."""

from __future__ import annotations


def formal_availability_validity(frequency_mhz, distance_km, los_blocked):
    """Return whether the formal availability path is valid for this case."""
    valid = frequency_mhz >= 3000.0 and distance_km > 0.0 and not los_blocked
    return {
        "valid": valid,
        "method": "formal_p530" if valid else "fallback_margin",
    }


def classify_fade_margin(margin_db):
    """Map fade margin to a user-facing class and summary."""
    if margin_db >= 15.0:
        return {"fade_margin_class": "Strong", "reliability_summary": "Reliable"}
    if margin_db >= 5.0:
        return {"fade_margin_class": "Moderate", "reliability_summary": "Reliable"}
    if margin_db >= 0.0:
        return {"fade_margin_class": "Low", "reliability_summary": "Marginal"}
    return {"fade_margin_class": "Weak", "reliability_summary": "Unreliable"}


def estimate_formal_availability_pct(margin_db, distance_km, frequency_mhz):
    """Return a bounded synthetic formal availability percentage."""
    value = 90.0 + margin_db * 0.4 - distance_km * 0.3 + frequency_mhz / 100000.0
    return max(0.0, min(100.0, round(value, 2)))


def summarize_reliability(margin_db, frequency_mhz, distance_km, los_blocked):
    """Return the method, availability estimate, and fallback classes."""
    validity = formal_availability_validity(
        frequency_mhz=frequency_mhz,
        distance_km=distance_km,
        los_blocked=los_blocked,
    )
    fallback = classify_fade_margin(margin_db)
    availability_estimate_pct = (
        estimate_formal_availability_pct(margin_db, distance_km, frequency_mhz)
        if validity["valid"]
        else None
    )
    return {
        "availability_method": validity["method"],
        "availability_estimate_pct": availability_estimate_pct,
        "fade_margin_class": fallback["fade_margin_class"],
        "reliability_summary": fallback["reliability_summary"],
    }
