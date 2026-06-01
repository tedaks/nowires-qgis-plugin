# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression tests for _compute_single_link edge cases.

Covers terminal-height out-of-range skip paths and EIRP/prx_dbm/margin_db math.
"""

import math

import pytest

from NoWires.fresnel import C_LIGHT
from NoWires.constants import MHZ_TO_HZ


class FakeElevGrid:
    def terrain_profile(self, lat1, lon1, lat2, lon2, step_m=30.0):
        pts = []
        for i in range(101):
            d = i * step_m
            e = 100.0 + 0.01 * d
            pts.append((d, e))
        return pts


class FakeParams:
    def __init__(self):
        self.tx_h = 30.0
        self.rx_h = 10.0
        self.f_mhz = 900.0
        self.polarization = 1
        self.climate = 1
        self.time_pct = 50.0
        self.location_pct = 50.0
        self.situation_pct = 50.0
        self.n0 = 301.0
        self.epsilon = 15.0
        self.sigma = 0.005
        self.k_factor = 1.33
        self.tx_power = 43.0
        self.tx_gain_default = 12.0
        self.rx_gain_default = 2.0
        self.cable_loss = 1.0
        self.rx_sens = -90.0
        self.tx_front_back_db = 25.0
        self.rx_front_back_db = 25.0
        self.tx_default_preset_key = "omni"
        self.rx_default_preset_key = "omni"
        self.tx_default_az = None
        self.rx_default_az = None
        self.clutter_enabled = False
        self.bel_enabled = False
        self.clutter_grid = None
        self.tx_clutter_override = None
        self.rx_clutter_override = None
        self.cch_override_m = None
        self.clutter_percentile = 50.0
        self.street_width_m = 15.0
        self.clutter_model = 0
        self.elev = FakeElevGrid()


def _build_tx_def(lat=45.0, lon=9.0, height=30.0):
    return {"lat": lat, "lon": lon, "height": height, "gain_db": None,
            "antenna_preset": "omni", "azimuth": None}


def _build_rx_def(lat=45.001, lon=9.001, height=10.0):
    return {"lat": lat, "lon": lon, "height": height, "gain_db": None,
            "antenna_preset": "omni", "azimuth": None}


class TestComputeSingleLinkEdges:
    def test_terminal_height_below_minimum_tx_returns_none(self):
        from batch.outputs import _compute_single_link

        tx_def = _build_tx_def(height=0.1)
        rx_def = _build_rx_def()
        params = FakeParams()
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
        assert result is None

    def test_terminal_height_above_maximum_rx_returns_none(self):
        from batch.outputs import _compute_single_link

        tx_def = _build_tx_def()
        rx_def = _build_rx_def(height=30000.0)
        params = FakeParams()
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
        assert result is None

    def test_too_close_less_than_1m_returns_none(self):
        from batch.outputs import _compute_single_link

        tx_def = _build_tx_def(lat=45.0, lon=9.0)
        rx_def = _build_rx_def(lat=45.0, lon=9.0000001)
        params = FakeParams()
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
        assert result is None

    def test_no_elev_grid_returns_none(self):
        from batch.outputs import _compute_single_link

        tx_def = _build_tx_def()
        rx_def = _build_rx_def()
        params = FakeParams()
        params.elev = None
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
        assert result is None

    def test_link_budget_math(self):
        from batch.outputs import _compute_single_link

        tx_def = _build_tx_def()
        rx_def = _build_rx_def()
        params = FakeParams()
        params.tx_power = 43.0
        params.tx_gain_default = 12.0
        params.cable_loss = 1.0
        params.rx_sens = -90.0
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
        assert result is not None
        assert "prx_dbm" in result
        assert "margin_db" in result
        assert "clearance_pct" in result
        assert "status" in result
        assert math.isfinite(result["prx_dbm"])
        assert math.isfinite(result["margin_db"])
        eirp = params.tx_power + params.tx_gain_default - params.cable_loss
        assert eirp == pytest.approx(54.0)
        assert result["margin_db"] == pytest.approx(
            result["prx_dbm"] - params.rx_sens, rel=1e-9)


class TestBatchLinkResults:
    def test_margin_db_sign_classifies_status(self):
        from batch.outputs import _compute_single_link

        tx_def = _build_tx_def()
        rx_def = _build_rx_def()
        params = FakeParams()
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        result = _compute_single_link(tx_def, rx_def, params, wavelength_m)
        assert result is not None
        if result["margin_db"] >= 0:
            assert result["status"] == "VIABLE"
        else:
            assert result["status"] == "NOT VIABLE"

    def test_omni_antenna_no_gain_adjustment(self):
        from batch.outputs import _compute_single_link

        params = FakeParams()
        wavelength_m = C_LIGHT / (params.f_mhz * MHZ_TO_HZ)

        tx_def_omni = _build_tx_def()
        rx_def_omni = _build_rx_def()
        result_omni = _compute_single_link(tx_def_omni, rx_def_omni, params, wavelength_m)

        params2 = FakeParams()
        tx_def_sector = _build_tx_def()
        tx_def_sector["antenna_preset"] = "sector_90"
        tx_def_sector["azimuth"] = 0.0
        rx_def_sector = _build_rx_def()
        rx_def_sector["antenna_preset"] = "omni"
        rx_def_sector["azimuth"] = None
        result_sector = _compute_single_link(tx_def_sector, rx_def_sector, params2, wavelength_m)

        assert result_omni is not None
        assert math.isfinite(result_omni["prx_dbm"])
        assert result_sector is not None
        assert math.isfinite(result_sector["prx_dbm"])
