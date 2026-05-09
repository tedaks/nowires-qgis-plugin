# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

"""Deprecated — use p2108_terrestrial_stat or p2108_height_gain instead.

This module is a thin shim that re-exports the P.2108-1 §3.2 statistical
clutter loss under the legacy names. It will be removed after one release cycle.
"""

import warnings

import numpy as np

from .p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat
from .p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat_vec

_DEPRECATED_NAMES = {
    "clutter_loss_p2108": clutter_loss_p2108_terrestrial_stat,
    "clutter_loss_p2108_vec": clutter_loss_p2108_terrestrial_stat_vec,
    "P2108_CATEGORY_PARAMS": {},
    "clutter_loss_p2108_terrestrial_stat": clutter_loss_p2108_terrestrial_stat,
    "clutter_loss_p2108_terrestrial_stat_vec": clutter_loss_p2108_terrestrial_stat_vec,
}


def clutter_loss_p2108(d_meter, category, f_mhz):
    warnings.warn(
        "clutter_loss_p2108 is deprecated — use clutter_loss_p2108_terrestrial_stat "
        "or p2108_height_gain.height_gain_loss",
        DeprecationWarning,
        stacklevel=2,
    )
    f_ghz = f_mhz / 1000.0
    d_km = d_meter / 1000.0
    if category == "open":
        return 0.0
    return clutter_loss_p2108_terrestrial_stat(d_km, f_ghz, p=50.0)


def clutter_loss_p2108_vec(distances_m, category, f_mhz):
    warnings.warn(
        "clutter_loss_p2108_vec is deprecated — use clutter_loss_p2108_terrestrial_stat_vec",
        DeprecationWarning,
        stacklevel=2,
    )
    f_ghz = f_mhz / 1000.0
    d_km_arr = np.asarray(distances_m, dtype=np.float64) / 1000.0
    if category == "open":
        return np.zeros_like(d_km_arr)
    return clutter_loss_p2108_terrestrial_stat_vec(d_km_arr, f_ghz, p=50.0)


P2108_CATEGORY_PARAMS = {}


def __getattr__(name):
    if name in _DEPRECATED_NAMES:
        warnings.warn(
            f"{name} from clutter_p2108 is deprecated",
            DeprecationWarning,
            stacklevel=2,
        )
        return _DEPRECATED_NAMES[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")