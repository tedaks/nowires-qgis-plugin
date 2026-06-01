# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
        email                : tedaks@gmail.com
 ***************************************************************************/

 Licensed under the MIT License; see the LICENSE file for the full text.


Antenna radiation pattern model.

Uses a simplified parabolic pattern within the main beam (3 dB roll-off
at beamwidth edges) and a fixed front-to-back ratio outside the beam.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)


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

    def __reduce__(self):
        # Explicit pickle support for cross-process transmission in
        # coverage multiprocessing workers. Returns a reconstruction
        # tuple that avoids any implicit state beyond the dataclass fields.
        return (
            AntennaConfig,
            (
                self.preset,
                self.azimuth_deg,
                self.horizontal_beamwidth_deg,
                self.vertical_beamwidth_deg,
                self.front_back_db,
                self.downtilt_deg,
                self.horizontal_pattern_path,
                self.vertical_pattern_path,
            ),
        )


ANTENNA_PRESETS = {
    "omni": AntennaPreset("omni", "Omni", 360.0, 360.0, 0.0),
    "sector_90": AntennaPreset("sector_90", "Sector 90", 90.0, 10.0, 25.0),
    "sector_120": AntennaPreset("sector_120", "Sector 120", 120.0, 10.0, 25.0),
    "dish_20": AntennaPreset("dish_20", "Dish 20", 20.0, 8.0, 35.0),
    "custom": AntennaPreset("custom", "Custom", 360.0, 360.0, 25.0),
}

ANTENNA_PRESET_OPTIONS = [preset.label for preset in ANTENNA_PRESETS.values()]
ANTENNA_PRESET_KEYS = list(ANTENNA_PRESETS.keys())

CUSTOM_ANTENNA_PRESET_INDEX = ANTENNA_PRESET_KEYS.index("custom")
MAX_PATTERN_ROWS = 3600


def _angle_diff_deg(angle_deg: float, reference_deg: float) -> float:
    """Compute the shortest angular difference in degrees, result in [-180, 180]."""
    return (angle_deg - reference_deg + 540.0) % 360.0 - 180.0


def antenna_preset_key(index_or_key: int | str) -> str:
    if isinstance(index_or_key, bool):
        raise TypeError("antenna_preset_key expects str or int, not bool")
    if isinstance(index_or_key, str):
        return index_or_key if index_or_key in ANTENNA_PRESETS else "omni"
    idx = int(index_or_key)
    if idx < 0 or idx >= len(ANTENNA_PRESET_KEYS):
        return "omni"
    return ANTENNA_PRESET_KEYS[idx]


def antenna_config_from_values(
    preset: int | str,
    azimuth_deg: float | None = None,
    horizontal_beamwidth_deg: float | None = None,
    vertical_beamwidth_deg: float | None = None,
    front_back_db: float | None = None,
    downtilt_deg: float = 0.0,
    horizontal_pattern_path: str | None = None,
    vertical_pattern_path: str | None = None,
) -> AntennaConfig:
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
def _read_pattern_points(path: str) -> list[tuple[float, float]]:
    """Read a CSV pattern file. Results are cached by path for the session;
    editing a pattern file requires calling clear_pattern_cache() or a QGIS
    restart to take effect."""
    points: list[tuple[float, float]] = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(points) >= MAX_PATTERN_ROWS:
                logger.warning(
                    "Pattern file %s exceeds %d rows; truncating", path, MAX_PATTERN_ROWS,
                )
                break
            if not row or len(row) < 2:
                continue
            try:
                angle = float(row[0])
                gain = float(row[1])
            except (ValueError, csv.Error):
                logger.warning("Skipping malformed row in pattern file %s: %s", path, row)
                continue
            points.append((angle, gain))
    if len(points) < 2:
        raise ValueError("Pattern file must contain at least two numeric rows.")
    return sorted(points)


def clear_pattern_cache() -> None:
    """Clear the LRU cache for antenna pattern files.

    Call this after editing a pattern CSV on disk to force re-reading
    on the next analysis run without requiring a QGIS restart."""
    _read_pattern_points.cache_clear()


def _interpolate_pattern_db(angle_deg: float, path: str, wrap: bool) -> float:
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
    bearing_from_tx_deg: float, az_deg: float | None, beamwidth_deg: float,
    front_back_db: float = 25.0,
) -> float:
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


def _vertical_gain_factor(elevation_angle_deg: float, downtilt_deg: float,
                         beamwidth_deg: float) -> float:
    if beamwidth_deg >= 360.0:
        return 0.0
    diff = elevation_angle_deg + downtilt_deg
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        return -(3.0 * x * x)
    return -12.0


def antenna_gain_adjustment_db(bearing_deg: float, elevation_angle_deg: float,
                               config: AntennaConfig | None) -> float:
    """Compute off-boresight antenna gain adjustment in dB.

    Returns a value <= 0.0 dB representing the gain reduction relative
    to the peak gain (which is already captured in tx_gain / rx_gain).
    Pattern CSVs MUST use gains *relative to peak* (i.e., always <= 0 dB).
    Positive gains in pattern files are silently clamped to 0.0.
    """
    if config is None:
        return 0.0
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
    result = horizontal + vertical
    if result > 0.0:
        logger.warning(
            "Antenna gain adjustment is positive (%.1f dB). "
            "Pattern files should use gains relative to peak. Clamping to 0.0 dB.",
            result,
        )
        return 0.0
    return result
