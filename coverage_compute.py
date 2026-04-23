# -*- coding: utf-8 -*-
"""
Coverage computation helpers built on the pure-Python ITM bridge.

Provides a narrow wrapper for point-to-point loss calculations used by
the coverage engine. The underlying propagation model remains in the
bundled pure-Python itm package for reliability and maintainability.
"""

import math

from .radio import build_pfl, itm_p2p_loss


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
    prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - result.loss_db
    return (result.loss_db, prx)
