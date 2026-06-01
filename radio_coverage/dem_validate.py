# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""DEM coverage validation for the Coverage Analysis algorithm.

Extracted from algorithm_coverage.py to keep that module within the
300-line cap.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def validate_dem_coverage(elev, south, north, west, east, feedback):
    """Warn if the DEM does not fully cover the requested analysis bounds."""
    dem_south = min(elev.min_lat, elev.max_lat)
    dem_north = max(elev.min_lat, elev.max_lat)
    dem_west = min(elev.min_lon, elev.max_lon)
    dem_east = max(elev.min_lon, elev.max_lon)
    uncovered_lat = (south < dem_south - 0.01) or (north > dem_north + 0.01)
    uncovered_lon = (west < dem_west - 0.01) or (east > dem_east + 0.01)
    if uncovered_lat or uncovered_lon:
        logger.warning(
            "DEM does not fully cover bounds. DEM: (%.4f,%.4f)-(%.4f,%.4f); "
            "Analysis: (%.4f,%.4f)-(%.4f,%.4f). Edge data may be unreliable.",
            dem_south, dem_west, dem_north, dem_east, south, west, north, east)
        feedback.pushWarning(
            "Downloaded DEM does not fully cover the analysis area. "
            "Results near the edges may be unreliable.")
