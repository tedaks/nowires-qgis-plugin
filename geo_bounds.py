# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Geographic bounding-box helpers for longitude wraparound."""

import logging
import math

from NoWires.constants import (
    AOI_PADDING_FRACTION, DEGREE_PADDING, MAX_AOI_EXTENT_DEGREES, METERS_PER_DEGREE_LAT,
)

logger = logging.getLogger(__name__)


def aoi_padding_deg(radius_m: float) -> float:
    """Return the standard AOI padding from a radius or distance in meters."""
    return float(max(DEGREE_PADDING, radius_m / METERS_PER_DEGREE_LAT * AOI_PADDING_FRACTION))


def coverage_bounds(tx_lat, tx_lon, radius_km, padding_deg=0.0, max_extent=MAX_AOI_EXTENT_DEGREES):
    """Compute the lat/lon bounding box for a coverage analysis.

    Returns (south, north, west, east) in degrees.
    Latitude bounds are clamped to [-90, 90] to handle near-pole TX
    positions where the analysis area would otherwise exceed valid range.
    The *max_extent* parameter caps the lat/lon span; if exceeded the bounds
    are clamped and a warning is logged.
    """
    radius_m = radius_km * 1000.0
    lat_per_m = 1.0 / METERS_PER_DEGREE_LAT
    lon_per_m = 1.0 / (METERS_PER_DEGREE_LAT * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = radius_m * lat_per_m
    half_lon = radius_m * lon_per_m
    if half_lat > max_extent:
        logger.warning("AOI lat extent clamped from %.2f to %.2f degrees", half_lat, max_extent)
        half_lat = max_extent
    if half_lon > max_extent:
        logger.warning("AOI lon extent clamped from %.2f to %.2f degrees", half_lon, max_extent)
        half_lon = max_extent
    south = max(-90.0, tx_lat - half_lat - padding_deg)
    north = min(90.0, tx_lat + half_lat + padding_deg)
    west = tx_lon - half_lon - padding_deg
    east = tx_lon + half_lon + padding_deg
    return (
        south,
        north,
        normalize_longitude(west),
        normalize_longitude(east),
    )


def validate_coordinates(lat, lon, label="point"):
    """Validate geographic coordinates are within valid ranges."""
    if lat < -90.0 or lat > 90.0:
        raise ValueError(
            "{} latitude {:.4f} is out of range [-90, 90].".format(label, lat))
    if lon < -180.0 or lon > 180.0:
        raise ValueError(
            "{} longitude {:.4f} is out of range [-180, 180].".format(label, lon))


def normalize_longitude(lon):
    """Return longitude normalized to [-180, 180)."""
    return ((float(lon) + 180.0) % 360.0) - 180.0


def longitude_intervals(west, east):
    """Split a longitude span into one or two non-wrapping intervals."""
    west = normalize_longitude(west)
    east = normalize_longitude(east)
    if west <= east:
        return [(west, east)]
    return [(west, 180.0), (-180.0, east)]


def shortest_longitude_bounds(lon_a, lon_b, padding_deg=0.0):
    """Return the shortest west/east bounds covering two longitudes.

    A returned ``west > east`` pair means the interval crosses the antimeridian.
    """
    return shortest_longitude_bounds_for([lon_a, lon_b], padding_deg=padding_deg)


def shortest_longitude_bounds_for(longitudes, padding_deg=0.0):
    """Return the shortest west/east bounds covering all longitudes."""
    values = [float(lon) % 360.0 for lon in longitudes]
    if not values:
        return -180.0, 180.0
    values = sorted(values)
    if len(values) == 1:
        west = values[0] - padding_deg
        east = values[0] + padding_deg
        return normalize_longitude(west), normalize_longitude(east)

    gaps = []
    for idx, value in enumerate(values):
        next_value = values[(idx + 1) % len(values)]
        if idx == len(values) - 1:
            next_value += 360.0
        gaps.append((next_value - value, idx))

    largest_gap, gap_idx = max(gaps)
    covered_span = 360.0 - largest_gap + (2.0 * padding_deg)
    if covered_span >= 360.0:
        return -180.0, 180.0

    start = values[(gap_idx + 1) % len(values)] - padding_deg
    end = values[gap_idx] + padding_deg
    if end < start:
        end += 360.0
    return normalize_longitude(start), normalize_longitude(end)
