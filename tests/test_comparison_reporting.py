# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for comparison_reporting: build_panel_info and build_delta_info."""


import numpy as np
import pytest

from comparison.reporting import build_panel_info, build_delta_info, validate_panels, resolve_output_paths


class TestBuildPanelInfo:
    def test_returns_all_expected_keys(self):
        panel = {
            "tx_lat": 14.0,
            "tx_lon": 121.0,
            "tx_h": 30.0,
            "rx_h": 10.0,
            "f_mhz": 900.0,
            "radius_km": 5.0,
            "tx_power": 43.0,
            "tx_gain": 8.0,
            "rx_gain": 2.0,
            "cable_loss": 2.0,
        }
        prx_grid = np.array([[-80.0, -70.0], [-90.0, np.nan]])
        info = build_panel_info(panel, prx_grid)
        assert "tx_lat" in info
        assert "rx_h" in info
        assert "valid_pixels" in info
        assert "total_pixels" in info
        assert "mean_prx" in info

    def test_counts_valid_pixels_excluding_nan(self):
        panel = {"tx_lat": 0, "tx_lon": 0, "tx_h": 10, "rx_h": 5,
                 "f_mhz": 900, "radius_km": 5, "tx_power": 43,
                 "tx_gain": 8, "rx_gain": 2, "cable_loss": 2}
        prx_grid = np.array([[1.0, np.nan], [3.0, 4.0]])
        info = build_panel_info(panel, prx_grid)
        assert info["valid_pixels"] == 3
        assert info["total_pixels"] == 4

    def test_mean_prx_is_nan_when_all_nan(self):
        panel = {"tx_lat": 0, "tx_lon": 0, "tx_h": 10, "rx_h": 5,
                 "f_mhz": 900, "radius_km": 5, "tx_power": 43,
                 "tx_gain": 8, "rx_gain": 2, "cable_loss": 2}
        prx_grid = np.full((2, 2), np.nan)
        info = build_panel_info(panel, prx_grid)
        assert np.isnan(info["mean_prx"])

    def test_mean_prx_computed_correctly(self):
        panel = {"tx_lat": 0, "tx_lon": 0, "tx_h": 10, "rx_h": 5,
                 "f_mhz": 900, "radius_km": 5, "tx_power": 43,
                 "tx_gain": 8, "rx_gain": 2, "cable_loss": 2}
        prx_grid = np.array([[10.0, 20.0]])
        info = build_panel_info(panel, prx_grid)
        assert info["mean_prx"] == pytest.approx(15.0)


class TestBuildDeltaInfo:
    def test_returns_all_expected_keys(self):
        ds = {
            "valid_count": 100,
            "improved": 30,
            "degraded": 20,
            "unchanged": 50,
            "min_delta": -15.0,
            "max_delta": 12.0,
            "mean_delta": -1.5,
        }
        info = build_delta_info("diverging", 5.0, ds)
        assert "style" in info
        assert "threshold_db" in info
        assert "valid_pixels" in info
        assert "improved_pixels" in info
        assert "degraded_pixels" in info
        assert "unchanged_pixels" in info
        assert "improved_pct" in info
        assert "degraded_pct" in info
        assert "unchanged_pct" in info
        assert "min_delta" in info
        assert "max_delta" in info
        assert "mean_delta" in info

    def test_percentages_are_computed(self):
        ds = {
            "valid_count": 100,
            "improved": 30,
            "degraded": 20,
            "unchanged": 50,
            "min_delta": -10.0,
            "max_delta": 10.0,
            "mean_delta": 0.0,
        }
        info = build_delta_info("threshold", 3.0, ds)
        assert info["improved_pct"] == pytest.approx(30.0)
        assert info["degraded_pct"] == pytest.approx(20.0)
        assert info["unchanged_pct"] == pytest.approx(50.0)

    def test_zero_valid_count_returns_zero_pcts(self):
        ds = {
            "valid_count": 0,
            "improved": 0,
            "degraded": 0,
            "unchanged": 0,
            "min_delta": 0.0,
            "max_delta": 0.0,
            "mean_delta": 0.0,
        }
        info = build_delta_info("diverging", 5.0, ds)
        assert info["improved_pct"] == 0.0
        assert info["degraded_pct"] == 0.0
        assert info["unchanged_pct"] == 0.0


@pytest.mark.qgis_integration
class TestValidatePanels:
    def test_co_located_positions_pass(self):
        from qgis.core import QgsPointXY
        a = QgsPointXY(121.0, 14.5)
        b = QgsPointXY(121.0, 14.5)
        validate_panels(a, b, 5.0, 5.0)

    def test_tx_positions_differ_beyond_tolerance_raises(self):
        from qgis.core import QgsPointXY, QgsProcessingException
        a = QgsPointXY(121.0, 14.5)
        b = QgsPointXY(121.0005, 14.5)  # 5e-4 > 1e-4 tolerance
        with pytest.raises(QgsProcessingException, match="TX positions differ"):
            validate_panels(a, b, 5.0, 5.0)

    def test_tx_positions_within_tolerance_pass(self):
        from qgis.core import QgsPointXY
        a = QgsPointXY(121.0, 14.5)
        b = QgsPointXY(121.0 + 5e-5, 14.5)  # 5e-5 < 1e-4 tolerance
        validate_panels(a, b, 5.0, 5.0)


class TestResolveOutputPaths:
    def test_asserts_tmpdir_not_none(self):
        class FakeTmpMgr:
            def make_dir(self, name, persistent=False):
                return None
        with pytest.raises(AssertionError):
            resolve_output_paths(
                None, None, None, None, None, FakeTmpMgr())

    def test_output_dir_provides_all_paths(self):
        import os
        import tempfile
        class FakeTmpMgr:
            def make_dir(self, name, persistent=False):
                return "/unused"
        with tempfile.TemporaryDirectory() as tmpdir:
            out_a, out_b, out_d = os.path.join(tmpdir, "a.tif"), os.path.join(tmpdir, "b.tif"), os.path.join(tmpdir, "d.tif")
            ra, rb, rd, _, _ = resolve_output_paths(
                tmpdir, out_a, out_b, out_d, None, FakeTmpMgr())
            assert ra == out_a
            assert rb == out_b
            assert rd == out_d
