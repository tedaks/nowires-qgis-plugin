# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 by Bortre Tenamo
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


Antenna radiation pattern model.

Uses a simplified parabolic pattern within the main beam (3 dB roll-off
at beamwidth edges) and a fixed front-to-back ratio outside the beam.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import csv
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class AntennaPreset:
    key: str
    label: str
    horizontal_beamwidth_deg: float
    vertical_beamwidth_deg: float
    front_back_db: float


@dataclass(frozen=True)
class AntennaConfig:
    preset: str = "omni"
    azimuth_deg: float | None = None
    horizontal_beamwidth_deg: float = 360.0
    vertical_beamwidth_deg: float = 360.0
    front_back_db: float = 25.0
    downtilt_deg: float = 0.0
    horizontal_pattern_path: str | None = None
    vertical_pattern_path: str | None = None


ANTENNA_PRESETS = {
    "omni": AntennaPreset("omni", "Omni", 360.0, 360.0, 0.0),
    "sector_90": AntennaPreset("sector_90", "Sector 90", 90.0, 10.0, 25.0),
    "sector_120": AntennaPreset("sector_120", "Sector 120", 120.0, 10.0, 25.0),
    "dish_20": AntennaPreset("dish_20", "Dish 20", 20.0, 8.0, 35.0),
    "custom": AntennaPreset("custom", "Custom", 360.0, 360.0, 25.0),
}

ANTENNA_PRESET_OPTIONS = [preset.label for preset in ANTENNA_PRESETS.values()]
ANTENNA_PRESET_KEYS = list(ANTENNA_PRESETS.keys())


def _angle_diff_deg(angle_deg, reference_deg):
    return (angle_deg - reference_deg + 540.0) % 360.0 - 180.0


def antenna_preset_key(index_or_key):
    if isinstance(index_or_key, str):
        return index_or_key if index_or_key in ANTENNA_PRESETS else "omni"
    idx = int(index_or_key)
    if idx < 0 or idx >= len(ANTENNA_PRESET_KEYS):
        return "omni"
    return ANTENNA_PRESET_KEYS[idx]


def antenna_config_from_values(
    preset,
    azimuth_deg=None,
    horizontal_beamwidth_deg=None,
    vertical_beamwidth_deg=None,
    front_back_db=None,
    downtilt_deg=0.0,
    horizontal_pattern_path=None,
    vertical_pattern_path=None,
):
    key = antenna_preset_key(preset)
    preset_value = ANTENNA_PRESETS[key]
    return AntennaConfig(
        preset=key,
        azimuth_deg=None if key == "omni" else azimuth_deg,
        horizontal_beamwidth_deg=(
            preset_value.horizontal_beamwidth_deg
            if horizontal_beamwidth_deg is None
            else horizontal_beamwidth_deg
        ),
        vertical_beamwidth_deg=(
            preset_value.vertical_beamwidth_deg
            if vertical_beamwidth_deg is None
            else vertical_beamwidth_deg
        ),
        front_back_db=(
            preset_value.front_back_db if front_back_db is None else front_back_db
        ),
        downtilt_deg=downtilt_deg,
        horizontal_pattern_path=horizontal_pattern_path or None,
        vertical_pattern_path=vertical_pattern_path or None,
    )


@lru_cache(maxsize=32)
def _read_pattern_points(path):
    points = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row or len(row) < 2:
                continue
            try:
                angle = float(row[0])
                gain = float(row[1])
            except ValueError:
                continue
            points.append((angle, gain))
    if len(points) < 2:
        raise ValueError("Pattern file must contain at least two numeric rows.")
    return sorted(points)


def _interpolate_pattern_db(angle_deg, path, wrap):
    points = _read_pattern_points(path)
    if wrap:
        angle = angle_deg % 360.0
        normalized = sorted((a % 360.0, g) for a, g in points)
        if normalized[0][0] != 0.0:
            normalized.insert(0, (0.0, normalized[-1][1]))
        if normalized[-1][0] != 360.0:
            normalized.append((360.0, normalized[0][1]))
        points = normalized
    else:
        angle = max(points[0][0], min(points[-1][0], angle_deg))

    for idx in range(len(points) - 1):
        a0, g0 = points[idx]
        a1, g1 = points[idx + 1]
        if a0 <= angle <= a1:
            if a1 == a0:
                return g0
            ratio = (angle - a0) / (a1 - a0)
            return g0 + (g1 - g0) * ratio
    return points[-1][1]


def antenna_gain_factor(
    bearing_from_tx_deg, az_deg, beamwidth_deg, front_back_db=25.0
):
    """Compute antenna gain adjustment in dB for a given bearing.

    Args:
        bearing_from_tx_deg: Bearing from TX to the target point (degrees).
        az_deg: Antenna main beam azimuth (degrees), or None for omni.
        beamwidth_deg: Antenna 3 dB beamwidth (degrees).
        front_back_db: Front-to-back ratio in dB.

    Returns:
        Gain adjustment in dB (0.0 for omni, negative for off-boresight).
    """
    if az_deg is None or beamwidth_deg >= 360.0:
        return 0.0
    diff = _angle_diff_deg(bearing_from_tx_deg, az_deg)
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        return -(3.0 * x * x)
    return -front_back_db


def _vertical_gain_factor(elevation_angle_deg, downtilt_deg, beamwidth_deg):
    if beamwidth_deg >= 360.0:
        return 0.0
    diff = elevation_angle_deg + downtilt_deg
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        return -(3.0 * x * x)
    return -12.0


def antenna_gain_adjustment_db(bearing_deg, elevation_angle_deg, config):
    if config.preset == "omni":
        return 0.0
    if config.horizontal_pattern_path:
        horizontal = _interpolate_pattern_db(
            _angle_diff_deg(bearing_deg, config.azimuth_deg or 0.0) % 360.0,
            config.horizontal_pattern_path,
            wrap=True,
        )
    else:
        horizontal = antenna_gain_factor(
            bearing_deg,
            config.azimuth_deg,
            config.horizontal_beamwidth_deg,
            config.front_back_db,
        )

    if config.vertical_pattern_path:
        vertical = _interpolate_pattern_db(
            elevation_angle_deg + config.downtilt_deg,
            config.vertical_pattern_path,
            wrap=False,
        )
    else:
        vertical = _vertical_gain_factor(
            elevation_angle_deg,
            config.downtilt_deg,
            config.vertical_beamwidth_deg,
        )
    return min(0.0, horizontal + vertical)