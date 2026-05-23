# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from unittest import mock

import numpy as np
import pytest


def _mock_qgis_utils_iface(iface_value):
    save = sys.modules.get("qgis.utils")
    mock_qgis = mock.MagicMock()
    mock_qgis.iface = iface_value
    sys.modules["qgis.utils"] = mock_qgis
    return save


def _restore_qgis_utils(saved):
    if saved is not None:
        sys.modules["qgis.utils"] = saved
    else:
        sys.modules.pop("qgis.utils", None)


@pytest.mark.qgis_integration
def test_on_destroy_registered_on_dock():
    """Behavioral: show_profile_chart runs with qgis.utils.iface available."""
    saved = _mock_qgis_utils_iface(mock.MagicMock())
    try:
        from NoWires.p2p.chart import show_profile_chart
        show_profile_chart(
            distances=np.array([0, 1000], dtype=np.float64),
            elevations=np.array([10, 10], dtype=np.float64),
            terrain_bulge=np.array([10, 10], dtype=np.float64),
            los_h=np.array([20, 20], dtype=np.float64),
            fresnel_r=np.array([1, 1], dtype=np.float64),
            dist_m=1000,
            tx_h=20, rx_h=20,
            f_mhz=900,
            result="LOS", k_factor=1.33,
            tx_power=30, tx_gain=10, rx_gain=10,
            cable_loss=2, rx_sens=-100,
        )
    finally:
        _restore_qgis_utils(saved)
