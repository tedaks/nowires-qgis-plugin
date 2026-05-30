# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Vegetation clutter loss — ITU-R P.833-9 §2.1.

P.833-9 §2.1 states that Am (maximum woodland attenuation) is
"equivalent to the clutter loss often quoted for a terminal obstructed by
some form of ground cover or clutter." Am is therefore the appropriate
value when the clutter raster classifies a pixel as vegetation but does
not supply the woodland-boundary-to-receiver path depth required for Eq. 1.

Am = A1 * f^alpha  (P.833-9 §2.1, Eq. 2)

St. Petersburg fit: A1=1.37, alpha=0.42, valid 105.9–2117.5 MHz.
Extrapolation outside this range is not sanctioned by the document.
"""
from __future__ import annotations


def clutter_loss_p833(cch_m: float, h_rx_m: float, f_mhz: float) -> float:
    """Vegetation clutter loss, ITU-R P.833-9 §2.1 Am.

    Returns Am when the receiver is below the canopy top, 0 otherwise.
    """
    if h_rx_m >= cch_m:
        return 0.0
    return 1.37 * (f_mhz ** 0.42)


def clutter_loss_p833_vec(
    cch_m: "np.ndarray | float",
    h_rx_m: "np.ndarray | float",
    f_mhz: "np.ndarray | float",
) -> "np.ndarray":
    """Vectorised clutter_loss_p833. Inputs broadcast to a common shape."""
    import numpy as np
    cch = np.asarray(cch_m, dtype=np.float64)
    hrx = np.asarray(h_rx_m, dtype=np.float64)
    f   = np.asarray(f_mhz,  dtype=np.float64)
    return np.where(hrx < cch, 1.37 * (f ** 0.42), 0.0)
