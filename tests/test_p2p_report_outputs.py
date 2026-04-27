# -*- coding: utf-8 -*-
"""Behavior tests for P2P report payloads and marker helpers."""

from report_payloads import (
    build_p2p_marker_records,
    build_p2p_report_payload,
    ogr_driver_for_path,
)


def test_ogr_driver_for_path_picks_extension():
    assert ogr_driver_for_path("foo.shp") == "ESRI Shapefile"
    assert ogr_driver_for_path("foo.gpkg") == "GPKG"
    assert ogr_driver_for_path("FOO.GPKG") == "GPKG"
    assert ogr_driver_for_path("foo.geojson") == "GeoJSON"
    assert ogr_driver_for_path("foo.json") == "GeoJSON"
    assert ogr_driver_for_path("foo.kml") == "KML"
    # Unknown / missing extensions default to GPKG (modern Processing default).
    assert ogr_driver_for_path("foo.unknown") == "GPKG"
    assert ogr_driver_for_path("foo") == "GPKG"


def test_build_p2p_report_payload_contains_expected_summary():
    payload = build_p2p_report_payload(
        tx_lat=14.0,
        tx_lon=121.0,
        rx_lat=14.1,
        rx_lon=121.1,
        tx_h=30.0,
        rx_h=10.0,
        f_mhz=900.0,
        polarization_name="Vertical",
        climate_name="Continental Subtropical",
        k_factor=1.3333333333,
        dist_m=12000.0,
        propagation_mode=1,
        propagation_mode_name="Line-of-Sight",
        fspl_db=113.1,
        itm_loss_db=121.4,
        tx_power=43.0,
        tx_gain=8.0,
        rx_gain=2.0,
        cable_loss=2.0,
        eirp_dbm=49.0,
        prx_dbm=-70.4,
        rx_sensitivity_dbm=-90.0,
        margin_db=19.6,
        los_blocked=False,
        fresnel_1_violated=False,
        fresnel_60_violated=False,
        max_fresnel_radius_m=8.4,
        total_path_loss_db=129.4,
        clutter_tx_db=2.0,
        clutter_rx_db=6.0,
        clutter_source="override",
        tx_antenna_preset="sector_90",
        rx_antenna_preset="omni",
        antenna_gain_adjustment_db=-1.0,
    )

    assert payload["report_type"] == "p2p"
    assert payload["inputs"]["frequency_mhz"] == 900.0
    assert payload["results"]["propagation_mode_name"] == "Line-of-Sight"
    assert payload["results"]["link_margin_db"] == 19.6
    assert payload["results"]["availability_method"] == "fallback_margin"
    assert payload["results"]["fade_margin_class"] == "Strong"
    assert payload["results"]["reliability_summary"] == "Reliable"
    assert payload["status"]["summary"] == "VIABLE"
    assert payload["results"]["clutter_tx_db"] == 2.0
    assert payload["results"]["clutter_rx_db"] == 6.0
    assert payload["results"]["total_path_loss_db"] == 129.4
    assert payload["inputs"]["tx_antenna_preset"] == "sector_90"


def test_build_p2p_marker_records_returns_tx_and_rx():
    rows = build_p2p_marker_records(
        tx_lat=14.0,
        tx_lon=121.0,
        rx_lat=14.1,
        rx_lon=121.1,
        tx_h=30.0,
        rx_h=10.0,
        tx_gain=8.0,
        rx_gain=2.0,
        tx_power_dbm=43.0,
        rx_sensitivity_dbm=-90.0,
    )

    assert [row["role"] for row in rows] == ["TX", "RX"]
    assert rows[0]["power_dbm"] == 43.0
    assert rows[1]["sensitivity_dbm"] == -90.0
