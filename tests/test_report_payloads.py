# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Comprehensive tests for report_payloads module."""

from unittest.mock import patch

from reliability import summarize_reliability
from report.payloads import (
    build_coverage_report_payload,
    build_empty_coverage_report_payload,
    build_p2p_report_payload,
    _build_coverage_input_dict,
    _build_coverage_reliability_results,
)


def _p2p_defaults(**overrides):
    defaults = dict(
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
    defaults.update(overrides)
    return defaults


class TestBuildP2pReportPayload:
    def test_positive_margin_gives_viable_status(self):
        p = build_p2p_report_payload(**_p2p_defaults(margin_db=5.0))
        assert p["status"]["summary"] == "VIABLE"
        assert p["status"]["viable"] is True

    def test_zero_margin_gives_viable_status(self):
        p = build_p2p_report_payload(**_p2p_defaults(margin_db=0.0))
        assert p["status"]["summary"] == "VIABLE"
        assert p["status"]["viable"] is True

    def test_negative_margin_gives_not_viable_status(self):
        p = build_p2p_report_payload(**_p2p_defaults(margin_db=-3.2))
        assert p["status"]["summary"] == "NOT VIABLE"
        assert p["status"]["viable"] is False

    def test_total_path_loss_db_defaults_to_itm_loss_db(self):
        p = build_p2p_report_payload(**_p2p_defaults(itm_loss_db=121.4))
        assert "total_path_loss_db" not in _p2p_defaults() or _p2p_defaults().get("total_path_loss_db") is None
        assert p["results"]["total_path_loss_db"] == 121.4

    def test_total_path_loss_db_uses_provided_value(self):
        p = build_p2p_report_payload(
            **_p2p_defaults(total_path_loss_db=129.4),
        )
        assert p["results"]["total_path_loss_db"] == 129.4

    def test_los_blocked_false_does_not_affect_validity(self):
        p = build_p2p_report_payload(**_p2p_defaults(los_blocked=False, margin_db=10.0))
        assert p["results"]["availability_method"] == "heuristic_availability"

    def test_los_blocked_true_forces_fallback_method(self):
        p = build_p2p_report_payload(**_p2p_defaults(los_blocked=True, margin_db=10.0))
        assert p["results"]["availability_method"] == "fallback_margin"
        assert p["results"]["availability_estimate_pct"] is None

    def test_los_blocked_is_converted_to_bool(self):
        p = build_p2p_report_payload(**_p2p_defaults(los_blocked=0))
        assert p["results"]["los_blocked"] is False

    def test_los_blocked_truthy_converted_to_bool(self):
        p = build_p2p_report_payload(**_p2p_defaults(los_blocked=1))
        assert p["results"]["los_blocked"] is True

    def test_fresnel_flags_converted_to_bool(self):
        p = build_p2p_report_payload(
            **_p2p_defaults(fresnel_1_violated=1, fresnel_60_violated=0),
        )
        assert p["results"]["fresnel_1_violated"] is True
        assert p["results"]["fresnel_60_violated"] is False

    def test_clutter_fields_default_correctly(self):
        p = build_p2p_report_payload(**_p2p_defaults())
        assert p["results"]["clutter_tx_db"] == 0.0
        assert p["results"]["clutter_rx_db"] == 0.0
        assert p["inputs"]["clutter_source"] == "off"

    def test_rounding_of_lat_lon_to_6_decimals(self):
        p = build_p2p_report_payload(**_p2p_defaults(
            tx_lat=14.123456789, tx_lon=121.987654321,
            rx_lat=14.111111111, rx_lon=121.222222222,
        ))
        assert p["inputs"]["tx_lat"] == 14.123457
        assert p["inputs"]["tx_lon"] == 121.987654
        assert p["inputs"]["rx_lat"] == 14.111111
        assert p["inputs"]["rx_lon"] == 121.222222

    def test_rounding_of_k_factor(self):
        p = build_p2p_report_payload(**_p2p_defaults(k_factor=1.333333333333))
        assert p["inputs"]["k_factor"] == round(1.333333333333, 6)

    def test_rounding_of_distance_km(self):
        p = build_p2p_report_payload(**_p2p_defaults(dist_m=12345.0))
        assert p["results"]["distance_km"] == 12.345
        assert p["results"]["distance_m"] == 12345.0

    def test_excess_loss_is_computed(self):
        p = build_p2p_report_payload(**_p2p_defaults(fspl_db=113.1, itm_loss_db=121.4))
        assert p["results"]["excess_loss_db"] == pytest.approx(121.4 - 113.1)

    def test_all_input_keys_present(self):
        p = build_p2p_report_payload(**_p2p_defaults())
        expected = {
            "tx_lat", "tx_lon", "rx_lat", "rx_lon",
            "tx_height_m", "rx_height_m", "frequency_mhz",
            "polarization", "climate", "k_factor",
            "tx_power_dbm", "tx_gain_dbi", "rx_gain_dbi",
            "cable_loss_db", "rx_sensitivity_dbm",
            "tx_antenna_preset", "rx_antenna_preset", "clutter_source",
        }
        assert expected.issubset(p["inputs"].keys())

    def test_all_result_keys_present(self):
        p = build_p2p_report_payload(**_p2p_defaults())
        expected = {
            "distance_m", "distance_km", "propagation_mode",
            "propagation_mode_name", "free_space_loss_db",
            "itm_path_loss_db", "excess_loss_db", "eirp_dbm",
            "clutter_tx_db", "clutter_rx_db", "total_path_loss_db",
            "antenna_gain_adjustment_db", "received_power_dbm",
            "link_margin_db", "availability_method",
            "availability_estimate_pct", "fade_margin_class",
            "reliability_summary", "los_blocked",
            "fresnel_1_violated", "fresnel_60_violated",
            "max_fresnel_radius_m", "tx_cch_m", "rx_cch_m",
            "clutter_method", "clutter_percentile", "bel_rx_db",
        }
        assert expected.issubset(p["results"].keys())


import pytest  # noqa: E402


class TestBuildCoverageInputDict:
    def _cov_input_kw(self, **overrides):
        kw = dict(
            tx_lat=14.123456789, tx_lon=121.987654321,
            tx_h=30.0, rx_h=10.0, f_mhz=1800.0,
            radius_km=5.0, grid_size=128,
            polarization_name="Vertical", climate_name="Continental Subtropical",
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=43.0, tx_gain=8.0, rx_gain=2.0,
            cable_loss=2.0, rx_sensitivity_dbm=-95.0,
            clutter_model="Off", clutter_source="off",
            tx_antenna_preset="omni",
        )
        kw.update(overrides)
        return kw

    def test_all_keys_present(self):
        d = _build_coverage_input_dict(**self._cov_input_kw())
        expected = {
            "tx_lat", "tx_lon", "tx_height_m", "rx_height_m",
            "frequency_mhz", "max_analysis_distance_km", "grid_size",
            "polarization", "climate", "time_pct", "location_pct",
            "situation_pct", "tx_power_dbm", "tx_gain_dbi",
            "rx_gain_dbi", "cable_loss_db", "rx_sensitivity_dbm",
            "clutter_model", "clutter_source", "tx_antenna_preset",
        }
        assert expected.issubset(d.keys())

    def test_rounding_of_lat_lon_to_6_decimals(self):
        d = _build_coverage_input_dict(**self._cov_input_kw(
            tx_lat=14.123456789, tx_lon=121.987654321,
        ))
        assert d["tx_lat"] == 14.123457
        assert d["tx_lon"] == 121.987654


class TestBuildCoverageReliabilityResults:
    def test_includes_extra_dict_items(self):
        reliability = summarize_reliability(
            margin_db=5.5, frequency_mhz=900.0,
            distance_km=12.0, los_blocked=False,
        )
        extra = {"usable_cell_count": 42, "pixel_count": 4096}
        results = _build_coverage_reliability_results(
            reliability, itm_loss_db=121.4, clutter_tx_db=2.0,
            clutter_rx_db=6.0, total_path_loss_db=129.4, extra=extra,
        )
        assert results["usable_cell_count"] == 42
        assert results["pixel_count"] == 4096

    def test_includes_reliability_derived_keys(self):
        reliability = summarize_reliability(
            margin_db=15.0, frequency_mhz=900.0,
            distance_km=12.0, los_blocked=False,
        )
        results = _build_coverage_reliability_results(
            reliability, itm_loss_db=100.0, clutter_tx_db=0.0,
            clutter_rx_db=0.0, total_path_loss_db=100.0, extra={},
        )
        assert results["availability_method"] == "heuristic_availability"
        assert results["fade_margin_class"] == "Strong"
        assert results["reliability_summary"] == "Reliable"
        assert isinstance(results["availability_estimate_pct"], float)

    def test_itm_loss_db_and_clutter_fields_passed_through(self):
        reliability = summarize_reliability(
            margin_db=5.0, frequency_mhz=900.0,
            distance_km=12.0, los_blocked=False,
        )
        results = _build_coverage_reliability_results(
            reliability, itm_loss_db=121.4, clutter_tx_db=2.5,
            clutter_rx_db=6.3, total_path_loss_db=130.2, extra={},
        )
        assert results["itm_loss_db"] == 121.4
        assert results["clutter_tx_db"] == 2.5
        assert results["clutter_rx_db"] == 6.3
        assert results["total_path_loss_db"] == 130.2


class TestBuildCoverageReportPayload:
    def _cov_defaults(self, **overrides):
        defaults = dict(
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
        )
        defaults.update(overrides)
        return defaults

    def test_usable_cells_gives_has_usable_cells_status(self):
        p = build_coverage_report_payload(**self._cov_defaults(usable_cell_count=5))
        assert p["status"]["summary"] == "HAS USABLE CELLS"
        assert p["status"]["usable_cells_present"] is True

    def test_zero_usable_cells_gives_no_usable_cells_status(self):
        p = build_coverage_report_payload(**self._cov_defaults(usable_cell_count=0))
        assert p["status"]["summary"] == "NO USABLE CELLS"
        assert p["status"]["usable_cells_present"] is False

    def test_rounding_in_inputs_lat_lon(self):
        p = build_coverage_report_payload(**self._cov_defaults(
            tx_lat=14.123456789, tx_lon=121.987654321,
        ))
        assert p["inputs"]["tx_lat"] == 14.123457
        assert p["inputs"]["tx_lon"] == 121.987654

    def test_results_include_coverage_specific_fields(self):
        p = build_coverage_report_payload(**self._cov_defaults())
        assert p["results"]["valid_pixel_count"] == 1000
        assert p["results"]["pixel_count"] == 4096
        assert p["results"]["usable_cell_count"] == 375
        assert p["results"]["min_prx_dbm"] == -121.0
        assert p["results"]["max_prx_dbm"] == -62.0
        assert p["results"]["mean_prx_dbm"] == -89.5

    def test_reliability_uses_mean_prx_margin(self):
        p = build_coverage_report_payload(**self._cov_defaults(
            mean_prx_dbm=-80.0, rx_sensitivity_dbm=-95.0,
        ))
        expected_reliability = summarize_reliability(
            margin_db=-80.0 - (-95.0),
            frequency_mhz=1800.0,
            distance_km=4.7,
            los_blocked=False,
        )
        assert p["results"]["availability_method"] == expected_reliability["availability_method"]
        assert p["results"]["fade_margin_class"] == expected_reliability["fade_margin_class"]


class TestBuildEmptyCoverageReportPayload:
    def _empty_defaults(self, **overrides):
        defaults = dict(
            tx_lat=14.0, tx_lon=121.0, tx_h=30.0, rx_h=10.0,
            f_mhz=1800.0, radius_km=5.0, grid_size=128,
            polarization_name="Vertical", climate_name="Continental Subtropical",
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=43.0, tx_gain=8.0, rx_gain=2.0,
            cable_loss=2.0, rx_sensitivity_dbm=-95.0,
            pixel_count=4096,
        )
        defaults.update(overrides)
        return defaults

    def test_uses_margin_db_negative_999_for_reliability(self):
        with patch("report.payloads.summarize_reliability") as mock_rel:
            mock_rel.return_value = dict(
                availability_method="fallback_margin",
                availability_estimate_pct=None,
                fade_margin_class="Weak",
                reliability_summary="Unreliable",
            )
            build_empty_coverage_report_payload(**self._empty_defaults())
            mock_rel.assert_called_once()
            call_kwargs = mock_rel.call_args[1]
            assert call_kwargs["margin_db"] == -999.0

    def test_zero_counts(self):
        p = build_empty_coverage_report_payload(**self._empty_defaults())
        assert p["results"]["valid_pixel_count"] == 0
        assert p["results"]["usable_cell_count"] == 0
        assert p["results"]["pct_above_sensitivity"] == 0.0

    def test_none_for_prx_fields(self):
        p = build_empty_coverage_report_payload(**self._empty_defaults())
        assert p["results"]["min_prx_dbm"] is None
        assert p["results"]["max_prx_dbm"] is None
        assert p["results"]["mean_prx_dbm"] is None

    def test_status_no_valid_coverage_cells(self):
        p = build_empty_coverage_report_payload(**self._empty_defaults())
        assert p["status"]["summary"] == "NO VALID COVERAGE CELLS"
        assert p["status"]["usable_cells_present"] is False

    def test_zero_distances(self):
        p = build_empty_coverage_report_payload(**self._empty_defaults())
        assert p["results"]["min_distance_km"] == 0.0
        assert p["results"]["max_distance_km"] == 0.0
        assert p["results"]["average_distance_km"] == 0.0

    def test_pixel_count_preserved(self):
        p = build_empty_coverage_report_payload(**self._empty_defaults(pixel_count=8192))
        assert p["results"]["pixel_count"] == 8192