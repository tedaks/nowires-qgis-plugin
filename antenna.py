# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2024 Bortre Tenamo
                               Adaptations (C) 2026 by Bortre Tenamo
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
    if az_deg is None:
        return 0.0
    diff = (bearing_from_tx_deg - az_deg + 540.0) % 360.0 - 180.0
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        attn = 3.0 * x * x
        return -attn
    return -front_back_db
