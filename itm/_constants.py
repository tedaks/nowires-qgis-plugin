# itm/_constants.py
"""
Derived from tedaks/pyitm, a Python port of NTIA's Irregular Terrain Model.
Original work: Copyright NTIA and distributed under the NTIA Software
Disclaimer / Release. Local adaptations are limited to plugin packaging and
import-path adjustments. See NOTICE.md for attribution details.
"""

from __future__ import annotations
import math

PI = 3.1415926535897932384
SQRT2 = math.sqrt(2)
THIRD = 1.0 / 3.0
a_0__meter = 6370e3  # actual earth radius
a_9000__meter = 9000e3  # reference radius for variability effective distance

# Wavenumber denominator: wn = f_mhz / WN_DENOM  [Algorithm]
WN_DENOM = 47.7

# InitializePointToPoint
GAMMA_A = 157e-9  # curvature of actual earth (~1/6370km)

# Variability
D_SCALE__meter = 100e3  # scale distance for sigma_S [Algorithm, Eqn 5.10]

# TroposcatterLoss
Z_0__meter = 1.7556e3  # scale height [Algorithm, 4.67]
Z_1__meter = 8.0e3  # [Algorithm, 4.67]
D_0__meter = 40e3  # troposcatter distance scale [Algorithm, 6.8]
TROPO_H__meter = 47.7  # height scale in troposcatter formula [Algorithm, 4.63]

# InitializeArea
H_3__meter = 5.0  # minimum effective height for horizon calc [Algorithm, Eqn 3.3]

# Warning bitmasks (matches Warnings.h)
WARN__TX_TERMINAL_HEIGHT = 0x0001
WARN__RX_TERMINAL_HEIGHT = 0x0002
WARN__FREQUENCY = 0x0004
WARN__PATH_DISTANCE_TOO_BIG_1 = 0x0008
WARN__PATH_DISTANCE_TOO_BIG_2 = 0x0010
WARN__PATH_DISTANCE_TOO_SMALL_1 = 0x0020
WARN__PATH_DISTANCE_TOO_SMALL_2 = 0x0040
WARN__TX_HORIZON_ANGLE = 0x0080
WARN__RX_HORIZON_ANGLE = 0x0100
WARN__TX_HORIZON_DISTANCE_1 = 0x0200
WARN__RX_HORIZON_DISTANCE_1 = 0x0400
WARN__TX_HORIZON_DISTANCE_2 = 0x0800
WARN__RX_HORIZON_DISTANCE_2 = 0x1000
WARN__EXTREME_VARIABILITIES = 0x2000
WARN__SURFACE_REFRACTIVITY = 0x4000

# Internal mode flags (not public)
MODE__P2P = 0
MODE__AREA = 1
