# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: coverage report payload must echo engine-consumed inputs."""

from NoWires.report.payloads import (
    build_coverage_report_payload,
    build_empty_coverage_report_payload,
    _build_coverage_input_dict,
)


class TestCoverageReportInputEcho:
    def test_inputs_include_n0_epsilon_sigma(self):
        payload = build_coverage_report_payload(
            tx_lat=14.5, tx_lon=121.0, tx_h=30.0, rx_h=1.5,
            f_mhz=900.0, radius_km=10.0, grid_size=128,
            polarization_name="Vertical", climate_name="Equatorial",
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=40.0, tx_gain=10.0, rx_gain=0.0,
            cable_loss=1.0, rx_sensitivity_dbm=-95.0,
            valid_pixel_count=100, pixel_count=1000,
            min_prx_dbm=-80.0, max_prx_dbm=-40.0, mean_prx_dbm=-60.0,
            pct_above_sensitivity=50.0, usable_cell_count=200,
            min_distance_km=0.1, max_distance_km=9.5,
            average_distance_km=5.0,
            n0=301.0, epsilon=15.0, sigma=0.005,
        )
        inputs = payload["inputs"]
        assert inputs["n0"] == 301.0
        assert inputs["epsilon"] == 15.0
        assert inputs["sigma"] == 0.005

    def test_inputs_include_clutter_and_antenna_params(self):
        payload = build_coverage_report_payload(
            tx_lat=14.5, tx_lon=121.0, tx_h=30.0, rx_h=1.5,
            f_mhz=900.0, radius_km=10.0, grid_size=128,
            polarization_name="Vertical", climate_name="Equatorial",
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=40.0, tx_gain=10.0, rx_gain=0.0,
            cable_loss=1.0, rx_sensitivity_dbm=-95.0,
            valid_pixel_count=100, pixel_count=1000,
            min_prx_dbm=-80.0, max_prx_dbm=-40.0, mean_prx_dbm=-60.0,
            pct_above_sensitivity=50.0, usable_cell_count=200,
            min_distance_km=0.1, max_distance_km=9.5,
            average_distance_km=5.0,
            antenna_az=45.0, antenna_bw_override=65.0,
            downtilt_deg=6.0, front_back_db=25.0,
            bel_enabled=True, bel_building_type="thermally_efficient",
            bel_elevation_angle_deg=30.0,
        )
        inputs = payload["inputs"]
        assert inputs["antenna_az"] == 45.0
        assert inputs["antenna_bw_override"] == 65.0
        assert inputs["downtilt_deg"] == 6.0
        assert inputs["bel_enabled"] is True
        assert inputs["bel_building_type"] == "thermally_efficient"

    def test_empty_payload_omits_extra_fields_by_default(self):
        payload = build_empty_coverage_report_payload(
            tx_lat=14.5, tx_lon=121.0, tx_h=30.0, rx_h=1.5,
            f_mhz=900.0, radius_km=10.0, grid_size=128,
            polarization_name="Vertical", climate_name="Equatorial",
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=40.0, tx_gain=10.0, rx_gain=0.0,
            cable_loss=1.0, rx_sensitivity_dbm=-95.0, pixel_count=1000,
        )
        inputs = payload["inputs"]
        assert inputs["n0"] is None
        assert inputs["epsilon"] is None

    def test_missing_extra_fields_are_none(self):
        inputs = _build_coverage_input_dict(
            tx_lat=0.0, tx_lon=0.0, tx_h=30.0, rx_h=10.0,
            f_mhz=900.0, radius_km=10.0, grid_size=128,
            polarization_name="Horizontal", climate_name="Desert",
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=40.0, tx_gain=10.0, rx_gain=0.0,
            cable_loss=1.0, rx_sensitivity_dbm=-95.0,
            clutter_model="Off", clutter_source="off", tx_antenna_preset="Omni",
        )
        assert inputs["bel_enabled"] is None
        assert inputs["clutter_percentile"] is None
