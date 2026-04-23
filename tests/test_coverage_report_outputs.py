# -*- coding: utf-8 -*-
"""Behavior tests for coverage report payloads."""

from report_payloads import build_coverage_report_payload


def test_build_coverage_report_payload_contains_summary_values():
    payload = build_coverage_report_payload(
        tx_lat=14.0,
        tx_lon=121.0,
        tx_h=30.0,
        rx_h=10.0,
        f_mhz=1800.0,
        radius_km=5.0,
        grid_size=128,
        polarization_name="Vertical",
        climate_name="Continental Subtropical",
        time_pct=50.0,
        location_pct=50.0,
        situation_pct=50.0,
        tx_power=43.0,
        tx_gain=8.0,
        rx_gain=2.0,
        cable_loss=2.0,
        rx_sensitivity_dbm=-95.0,
        valid_pixel_count=1000,
        pixel_count=4096,
        min_prx_dbm=-121.0,
        max_prx_dbm=-62.0,
        mean_prx_dbm=-89.5,
        pct_above_sensitivity=37.5,
        usable_cell_count=375,
        min_distance_km=0.2,
        max_distance_km=4.7,
        average_distance_km=2.6,
    )

    assert payload["report_type"] == "coverage"
    assert payload["inputs"]["grid_size"] == 128
    assert payload["results"]["usable_cell_count"] == 375
    assert payload["status"]["summary"] == "HAS USABLE CELLS"
