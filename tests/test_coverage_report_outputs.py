# -*- coding: utf-8 -*-
"""Behavior tests for coverage report payloads."""

from report_payloads import (
    build_coverage_report_payload,
    build_empty_coverage_report_payload,
)


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
        clutter_model="Simple clutter correction",
        clutter_source="memory",
        tx_antenna_preset="sector_120",
        itm_loss_db=118.0,
        clutter_tx_db=2.0,
        clutter_rx_db=6.0,
        total_path_loss_db=126.0,
    )

    assert payload["report_type"] == "coverage"
    assert payload["inputs"]["grid_size"] == 128
    assert payload["results"]["usable_cell_count"] == 375
    assert payload["results"]["availability_method"] == "fallback_margin"
    assert payload["results"]["reliability_summary"] == "Reliable"
    assert payload["status"]["summary"] == "HAS USABLE CELLS"
    assert payload["inputs"]["clutter_model"] == "Simple clutter correction"
    assert payload["inputs"]["clutter_source"] == "memory"
    assert payload["inputs"]["tx_antenna_preset"] == "sector_120"
    assert payload["results"]["itm_loss_db"] == 118.0
    assert payload["results"]["clutter_tx_db"] == 2.0
    assert payload["results"]["clutter_rx_db"] == 6.0
    assert payload["results"]["total_path_loss_db"] == 126.0


def test_build_empty_coverage_report_payload_records_failed_grid_without_fake_stats():
    payload = build_empty_coverage_report_payload(
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
        pixel_count=4096,
    )

    assert payload["results"]["valid_pixel_count"] == 0
    assert payload["results"]["min_prx_dbm"] is None
    assert payload["results"]["pct_above_sensitivity"] == 0.0
    assert payload["results"]["usable_cell_count"] == 0
    assert payload["status"]["summary"] == "NO VALID COVERAGE CELLS"
