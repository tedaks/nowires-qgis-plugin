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


Coverage computation helpers built on the pure-Python ITM bridge.

Provides a narrow wrapper for point-to-point loss calculations used by
the coverage engine. The underlying propagation model remains in the
bundled pure-Python itm package for reliability and maintainability.
"""

import math

import numpy as np

from .radio import build_pfl, itm_p2p_loss

DEFAULT_PROFILE_STEP_M = 100.0
DEFAULT_MAX_PROFILE_PTS = 200


COVERAGE_NODATA = -9999.0
"""NoData sentinel for coverage rasters.

Chosen because GDAL's Float32 NoData requires a finite value (NaN is not
universally supported as NoData in all GDAL drivers/formats).  -9999 is
well outside both valid path-loss range (0–400 dB) and received-power
range (≈-120 to +80 dBm), so it cannot be confused with legitimate
values.  If this raster is later used as input to another computation,
its NoData flag must be explicitly masked via GDAL or numpy before
arithmetic operations.
"""


def grid_to_raster_array(grid, nodata=COVERAGE_NODATA):
    """Return a top-origin raster array with missing cells encoded as nodata.

    Uses *nodata* (default -9999) rather than NaN because many GIS formats
    and GDAL drivers do not reliably round-trip NaN NoData values for
    Float32 rasters.  Callers that consume the raster programmatically
    should treat *nodata* as missing.
    """
    arr = np.asarray(grid, dtype=np.float32)
    return np.where(np.isnan(arr), nodata, arr)[::-1]


def coverage_profile_step_m(f_mhz):
    """Profile sampling step (metres) used by the coverage analysis.

    Kept as a function (not a bare constant) so callers don't bake the
    sampling policy into call sites. Future tuning (e.g. frequency-aware
    step sizing) lives here without touching the algorithm wiring.
    """
    del f_mhz  # currently constant; argument reserved for future tuning
    return DEFAULT_PROFILE_STEP_M


def compute_itm_p2p(
    h_tx__meter,
    h_rx__meter,
    elevations,
    resolution,
    climate_idx,
    N_0,
    f__mhz,
    polarization,
    epsilon,
    sigma,
    time_pct,
    location_pct,
    situation_pct,
    eirp_dbm,
    ant_gain_adj,
    rx_gain_dbi,
    clutter_tx_db=0.0,
    clutter_rx_db=0.0,
):
    """Compute ITM point-to-point loss and received power."""
    elev_list = (
        elevations.tolist() if hasattr(elevations, "tolist") else list(elevations)
    )
    pfl = build_pfl(elev_list, resolution)
    result = itm_p2p_loss(
        h_tx__meter=h_tx__meter,
        h_rx__meter=h_rx__meter,
        profile=pfl,
        climate=climate_idx,
        N0=N_0,
        f__mhz=f__mhz,
        polarization=polarization,
        epsilon=epsilon,
        sigma=sigma,
        time_pct=time_pct,
        location_pct=location_pct,
        situation_pct=situation_pct,
    )
    if not math.isfinite(result.loss_db) or result.loss_db > 400.0:
        return None
    clutter_total_db = clutter_tx_db + clutter_rx_db
    total_path_loss_db = result.loss_db + clutter_total_db
    prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - total_path_loss_db
    return {
        "itm_loss_db": result.loss_db,
        "clutter_tx_db": clutter_tx_db,
        "clutter_rx_db": clutter_rx_db,
        "total_path_loss_db": total_path_loss_db,
        "antenna_gain_adjustment_db": ant_gain_adj,
        "received_power_dbm": prx,
    }
