# itm/models.py
"""
Derived from tedaks/pyitm, a Python port of NTIA's Irregular Terrain Model.
Original work: Copyright NTIA and distributed under the NTIA Software
Disclaimer / Release. Local adaptations are limited to plugin packaging and
import-path adjustments. See NOTICE.md for attribution details.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import IntFlag, IntEnum
import numpy as np

logger = logging.getLogger(__name__)


class Climate(IntEnum):
    EQUATORIAL = 1
    CONTINENTAL_SUBTROPICAL = 2
    MARITIME_SUBTROPICAL = 3
    DESERT = 4
    CONTINENTAL_TEMPERATE = 5
    MARITIME_TEMPERATE_LAND = 6
    MARITIME_TEMPERATE_SEA = 7


class Polarization(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1


class MDVar(IntEnum):
    SINGLE_MESSAGE = 0
    ACCIDENTAL = 1
    MOBILE = 2
    BROADCAST = 3


class PropMode(IntEnum):
    LINE_OF_SIGHT = 1
    DIFFRACTION = 2
    TROPOSCATTER = 3


class SitingCriteria(IntEnum):
    RANDOM = 0
    CAREFUL = 1
    VERY_CAREFUL = 2


class Warnings(IntFlag):
    TX_TERMINAL_HEIGHT = 0x0001
    RX_TERMINAL_HEIGHT = 0x0002
    FREQUENCY = 0x0004
    PATH_DISTANCE_TOO_BIG_1 = 0x0008
    PATH_DISTANCE_TOO_BIG_2 = 0x0010
    PATH_DISTANCE_TOO_SMALL_1 = 0x0020
    PATH_DISTANCE_TOO_SMALL_2 = 0x0040
    TX_HORIZON_ANGLE = 0x0080
    RX_HORIZON_ANGLE = 0x0100
    TX_HORIZON_DISTANCE_1 = 0x0200
    RX_HORIZON_DISTANCE_1 = 0x0400
    TX_HORIZON_DISTANCE_2 = 0x0800
    RX_HORIZON_DISTANCE_2 = 0x1000
    EXTREME_VARIABILITIES = 0x2000
    SURFACE_REFRACTIVITY = 0x4000
    NONE = 0


@dataclass(frozen=True)
class TerrainProfile:
    """Terrain elevation profile in PFL format."""

    elevations: np.ndarray
    resolution: float

    @classmethod
    def from_pfl(cls, pfl: list[float]) -> TerrainProfile:
        """Construct from raw C-style PFL array.

        pfl[0]   = number of elevation intervals (np), so np+1 points total
        pfl[1]   = resolution in meters
        pfl[2+]  = elevation values (np+1 values at pfl[2]..pfl[np+2])
        """
        if len(pfl) < 3:
            raise ValueError(
                f"PFL array must have at least 3 elements (np, resolution, one elevation), got {len(pfl)}"
            )
        np_ = int(pfl[0])
        if np_ < 1:
            raise ValueError(f"PFL interval count must be >= 1, got {np_}")
        available = len(pfl) - 2
        if available < 2:
            raise ValueError(
                f"pfl has only {available} elevation values, need at least 2 for 1 interval"
            )
        resolution = float(pfl[1])
        if available >= np_ + 1:
            elevations = np.asarray(pfl[2 : np_ + 3], dtype=float)
        else:
            actual_np = min(np_, available - 1)
            elevations = np.asarray(pfl[2 : 2 + actual_np + 1], dtype=float)
            logger.warning(
                "PFL data truncated: header declares %d elevation intervals "
                "(%d points) but only %d values available; using %d points",
                np_, np_ + 1, available, actual_np + 1,
            )
        return cls(elevations=elevations, resolution=resolution)


@dataclass(frozen=True)
class IntermediateValues:
    theta_hzn: tuple[float, float]
    d_hzn__meter: tuple[float, float]
    h_e__meter: tuple[float, float]
    N_s: float
    delta_h__meter: float
    A_ref__db: float
    A_fs__db: float
    d__km: float
    mode: PropMode


@dataclass(frozen=True)
class PropagationResult:
    A__db: float
    warnings: int
    intermediate: IntermediateValues | None = None
