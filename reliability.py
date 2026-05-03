# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
        email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/


Pure-Python helpers for NoWires reliability outputs.

The availability percentage exposed here is a heuristic blend of fade
margin, distance, and frequency. It is **not** a faithful implementation
of ITU-R P.530 and should NOT be relied upon for link budget engineering.
See ``estimate_heuristic_availability_pct`` for the formula and caveats.
The method label reflects this: ``heuristic_availability`` when the
preconditions for an availability estimate are met (unobstructed LOS),
``fallback_margin`` otherwise.
"""

from __future__ import annotations


def heuristic_availability_validity(frequency_mhz, distance_km, los_blocked):
    """Return whether a heuristic availability estimate is meaningful here.

    The preconditions (non-zero distance, unobstructed LOS) gate whether
    the heuristic blend below produces a number, not whether the link is
    actually reliable.  The frequency term in the formula already provides
    a natural penalty for higher bands, so no minimum-frequency gate is
    applied.
    """
    valid = distance_km > 0.0 and not los_blocked
    return {
        "valid": valid,
        "method": "heuristic_availability" if valid else "fallback_margin",
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


def estimate_heuristic_availability_pct(margin_db, distance_km, frequency_mhz):
    """Return a bounded heuristic availability percentage in [0, 100].

    **Disclaimer:** This is a rough heuristic, NOT an ITU-R P.530 calculation.
    The value should NOT be relied upon for link budget engineering.
    The frequency term naturally penalizes higher bands; no minimum-frequency
    gate is applied.  Replace with a P.530-derived calculation if/when
    authoritative availability estimates are needed.
    """
    value = 90.0 + margin_db * 0.4 - distance_km * 0.3 - frequency_mhz / 100000.0
    return max(0.0, min(100.0, round(value, 2)))


def summarize_reliability(margin_db, frequency_mhz, distance_km, los_blocked):
    """Return the method, availability estimate, and fallback classes."""
    validity = heuristic_availability_validity(
        frequency_mhz=frequency_mhz,
        distance_km=distance_km,
        los_blocked=los_blocked,
    )
    fallback = classify_fade_margin(margin_db)
    availability_estimate_pct = (
        estimate_heuristic_availability_pct(margin_db, distance_km, frequency_mhz)
        if validity["valid"]
        else None
    )
    return {
        "availability_method": validity["method"],
        "availability_estimate_pct": availability_estimate_pct,
        "fade_margin_class": fallback["fade_margin_class"],
        "reliability_summary": fallback["reliability_summary"],
    }
