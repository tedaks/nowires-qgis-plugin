# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test: P2P and coverage report payloads use consistent JSON key for ITM loss.

Before v1.6.5, P2P reports used ``"itm_path_loss_db"`` while coverage reports
used ``"itm_loss_db"``.  Both must now use ``"itm_loss_db"``.
"""

from report.payloads import build_coverage_report_payload, build_p2p_report_payload


def test_p2p_payload_uses_itm_loss_db():
    p = build_p2p_report_payload(
        tx_lat=14.0, tx_lon=121.0, rx_lat=14.1, rx_lon=121.1,
        tx_h=30.0, rx_h=10.0, f_mhz=900.0,
        polarization_name="Vertical", climate_name="Continental Subtropical",
        k_factor=1.3333333333, dist_m=12000.0,
        propagation_mode=1, propagation_mode_name="Line-of-Sight",
        fspl_db=113.1, itm_loss_db=121.4,
        tx_power=43.0, tx_gain=8.0, rx_gain=2.0,
        cable_loss=2.0, eirp_dbm=49.0,
        prx_dbm=-70.4, rx_sensitivity_dbm=-90.0,
        margin_db=19.6, los_blocked=False,
        fresnel_1_violated=False, fresnel_60_violated=False,
        max_fresnel_radius_m=8.4,
    )
    assert "itm_loss_db" in p["results"], "P2P payload must contain itm_loss_db"
    assert isinstance(p["results"]["itm_loss_db"], (int, float))
    assert p["results"]["itm_loss_db"] == 121.4


def test_coverage_payload_uses_itm_loss_db():
    p = build_coverage_report_payload(
        tx_lat=14.0, tx_lon=121.0, tx_h=30.0, rx_h=10.0,
        f_mhz=1800.0, radius_km=5.0, grid_size=128,
        polarization_name="Vertical", climate_name="Continental Subtropical",
        time_pct=50.0, location_pct=50.0, situation_pct=50.0,
        tx_power=43.0, tx_gain=8.0, rx_gain=2.0,
        cable_loss=2.0, rx_sensitivity_dbm=-95.0,
        valid_pixel_count=1000, pixel_count=4096,
        min_prx_dbm=-121.0, max_prx_dbm=-62.0, mean_prx_dbm=-89.5,
        pct_above_sensitivity=37.5, usable_cell_count=375,
        min_distance_km=0.2, max_distance_km=4.7,
        average_distance_km=2.6,
        itm_loss_db=115.0,
    )
    assert "itm_loss_db" in p["results"], "Coverage payload must contain itm_loss_db"
    assert isinstance(p["results"]["itm_loss_db"], (int, float))
    assert p["results"]["itm_loss_db"] == 115.0


def test_p2p_payload_does_not_contain_old_key():
    p = build_p2p_report_payload(
        tx_lat=14.0, tx_lon=121.0, rx_lat=14.1, rx_lon=121.1,
        tx_h=30.0, rx_h=10.0, f_mhz=900.0,
        polarization_name="Vertical", climate_name="Continental Subtropical",
        k_factor=1.3333333333, dist_m=12000.0,
        propagation_mode=1, propagation_mode_name="Line-of-Sight",
        fspl_db=113.1, itm_loss_db=121.4,
        tx_power=43.0, tx_gain=8.0, rx_gain=2.0,
        cable_loss=2.0, eirp_dbm=49.0,
        prx_dbm=-70.4, rx_sensitivity_dbm=-90.0,
        margin_db=19.6, los_blocked=False,
        fresnel_1_violated=False, fresnel_60_violated=False,
        max_fresnel_radius_m=8.4,
    )
    assert "itm_path_loss_db" not in p["results"], (
        "P2P payload must not use the old key itm_path_loss_db"
    )


def test_coverage_payload_does_not_contain_old_key():
    p = build_coverage_report_payload(
        tx_lat=14.0, tx_lon=121.0, tx_h=30.0, rx_h=10.0,
        f_mhz=1800.0, radius_km=5.0, grid_size=128,
        polarization_name="Vertical", climate_name="Continental Subtropical",
        time_pct=50.0, location_pct=50.0, situation_pct=50.0,
        tx_power=43.0, tx_gain=8.0, rx_gain=2.0,
        cable_loss=2.0, rx_sensitivity_dbm=-95.0,
        valid_pixel_count=1000, pixel_count=4096,
        min_prx_dbm=-121.0, max_prx_dbm=-62.0, mean_prx_dbm=-89.5,
        pct_above_sensitivity=37.5, usable_cell_count=375,
        min_distance_km=0.2, max_distance_km=4.7,
        average_distance_km=2.6,
        itm_loss_db=115.0,
    )
    assert "itm_path_loss_db" not in p["results"], (
        "Coverage payload must not use the old key itm_path_loss_db"
    )
