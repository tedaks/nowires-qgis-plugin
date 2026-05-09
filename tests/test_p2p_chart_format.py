# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for p2p_chart_format: obstruction data extraction and status text."""

import types

import numpy as np
import pytest

from p2p_chart_format import build_obstruction_data, build_chart_status_text


class TestBuildObstructionDataNoObstructions:
    """Terrain is entirely below LOS-Fresnel zone."""

    def test_flat_terrain_below_los(self):
        d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        terrain_bulge = np.array([10.0, 10.0, 10.0, 10.0, 10.0])
        los_h = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert result == []

    def test_terrain_approaching_but_not_reaching_los_minus_fresnel(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([50.0, 94.9, 50.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert result == []

    def test_terrain_exactly_at_los_minus_fresnel_is_not_obstruction(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([50.0, 95.0, 50.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert result == []


class TestBuildObstructionDataSinglePeak:
    """Single peak that just barely exceeds LOS-Fresnel zone."""

    def test_single_peak_obstruction(self):
        d_km = np.array([0.0, 2.5, 5.0, 7.5, 10.0])
        terrain_bulge = np.array([20.0, 60.0, 96.0, 55.0, 15.0])
        los_h = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        idx, d, tb, lh, fr, deficit = result[0]
        assert idx == 2
        assert d == pytest.approx(5.0)
        assert tb == pytest.approx(96.0)
        assert lh == pytest.approx(100.0)
        assert fr == pytest.approx(5.0)
        assert deficit == pytest.approx(1.0)

    def test_single_peak_with_larger_deficit(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([30.0, 120.0, 30.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        idx, d, tb, lh, fr, deficit = result[0]
        assert idx == 1
        assert deficit == pytest.approx(25.0)

    def test_edge_point_obstruction(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([96.0, 50.0, 30.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        assert result[0][0] == 0


class TestBuildObstructionDataMultiplePeaks:
    """Multiple peaks: returned sorted by terrain_bulge descending, up to 5."""

    def test_two_peaks_sorted_by_height(self):
        d_km = np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0])
        terrain_bulge = np.array([30.0, 97.0, 50.0, 99.0, 50.0, 20.0])
        los_h = np.full(6, 100.0)
        fresnel_r = np.full(6, 5.0)
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 2
        assert result[0][0] == 3
        assert result[1][0] == 1

    def test_three_peaks_sorted_descending(self):
        d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        terrain_bulge = np.array([10.0, 97.0, 50.0, 98.0, 55.0, 99.0, 50.0, 10.0])
        los_h = np.full(8, 100.0)
        fresnel_r = np.full(8, 5.0)
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 3
        heights = [r[2] for r in result]
        assert heights == [99.0, 98.0, 97.0]

    def test_at_most_five_peaks_returned(self):
        d_km = np.arange(0.0, 22.0, 1.0)
        terrain_bulge = np.full(22, 50.0)
        los_h = np.full(22, 100.0)
        fresnel_r = np.full(22, 5.0)
        peak_indices = [1, 3, 5, 7, 9, 11, 13]
        for i in peak_indices:
            terrain_bulge[i] = 95.0 + i * 2
        flat_indices = [i for i in range(22) if i not in peak_indices]
        for i in flat_indices:
            terrain_bulge[i] = 50.0
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) <= 5
        if len(result) > 0:
            assert result[0][2] >= result[-1][2]

    def test_six_peaks_returns_top_five(self):
        d_km = np.arange(14, dtype=float)
        terrain_bulge = np.array([
            50.0, 96.0, 50.0, 97.0, 50.0, 98.0,
            50.0, 99.0, 50.0, 100.5, 50.0, 101.0, 50.0, 102.0,
        ])
        los_h = np.full(14, 100.0)
        fresnel_r = np.full(14, 5.0)
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 5
        heights = [r[2] for r in result]
        assert heights == sorted(heights, reverse=True)


class TestBuildObstructionDataFlatAtLOS:
    """Terrain at LOS level: all points are obstructions."""

    def test_flat_at_los_all_points_are_obstructions(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([100.0, 100.0, 100.0])
        los_h = np.array([95.0, 95.0, 95.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) >= 1

    def test_flat_plateau_all_obstructed_single_peak_at_left_edge(self):
        d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        terrain_bulge = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        los_h = np.full(5, 95.0)
        fresnel_r = np.full(5, 5.0)
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        assert result[0][0] == 0


class TestBuildObstructionDataPlateau:
    """Plateau terrain: only the edge is a peak, interior is not."""

    def test_plateau_edge_is_peak(self):
        d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        terrain_bulge = np.array([20.0, 96.0, 96.0, 96.0, 96.0, 60.0, 20.0])
        los_h = np.full(7, 100.0)
        fresnel_r = np.full(7, 5.0)
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        peak_indices = [r[0] for r in result]
        assert 1 in peak_indices
        for idx in [2, 3, 4]:
            assert idx not in peak_indices

    def test_plateau_right_edge_descending_is_peak(self):
        d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        terrain_bulge = np.array([20.0, 60.0, 95.0, 96.0, 20.0])
        los_h = np.full(5, 100.0)
        fresnel_r = np.full(5, 5.0)
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        peak_indices = [r[0] for r in result]
        assert 3 in peak_indices
        assert 2 not in peak_indices


class TestBuildObstructionDataDeficit:
    """Deficit is max(0, terrain - (los - fresnel))."""

    def test_deficit_positive(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([30.0, 110.0, 30.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        assert result[0][5] == pytest.approx(15.0)

    def test_deficit_clamped_to_zero(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([30.0, 96.0, 30.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([5.0, 5.0, 5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        assert result[0][5] == pytest.approx(1.0)

    def test_deficit_fresnel_zone_width_matters(self):
        d_km = np.array([0.0, 5.0, 10.0])
        terrain_bulge = np.array([30.0, 110.0, 30.0])
        los_h = np.array([100.0, 100.0, 100.0])
        fresnel_r = np.array([10.0, 10.0, 10.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        assert result[0][5] == pytest.approx(20.0)


class TestBuildObstructionDataSinglePointArrays:
    """Single-point arrays: edge case for peak detection."""

    def test_single_point_not_obstructing(self):
        d_km = np.array([5.0])
        terrain_bulge = np.array([50.0])
        los_h = np.array([100.0])
        fresnel_r = np.array([5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert result == []

    def test_single_point_obstructing(self):
        d_km = np.array([5.0])
        terrain_bulge = np.array([110.0])
        los_h = np.array([100.0])
        fresnel_r = np.array([5.0])
        result = build_obstruction_data(d_km, terrain_bulge, los_h, fresnel_r)
        assert len(result) == 1
        assert result[0][0] == 0
        assert result[0][5] == pytest.approx(15.0)


class TestBuildChartStatusTextViable:
    """Positive margin yields VIABLE status."""

    def test_positive_margin(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, 10.0)
        assert "VIABLE" in text
        assert "NOT VIABLE" not in text

    def test_positive_margin_includes_all_fields(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, 10.0)
        assert "Loss: 120.0 dB" in text
        assert "Prx: -60.0 dBm" in text
        assert "Margin: 10.0 dB" in text
        assert "Status: VIABLE" in text


class TestBuildChartStatusTextNotViable:
    """Negative margin yields NOT VIABLE status."""

    def test_negative_margin(self):
        result = types.SimpleNamespace(loss_db=140.0)
        text = build_chart_status_text(result, -80.0, -5.0)
        assert "NOT VIABLE" in text

    def test_negative_margin_includes_all_fields(self):
        result = types.SimpleNamespace(loss_db=140.0)
        text = build_chart_status_text(result, -80.0, -5.0)
        assert "Loss: 140.0 dB" in text
        assert "Prx: -80.0 dBm" in text
        assert "Margin: -5.0 dB" in text
        assert "Status: NOT VIABLE" in text


class TestBuildChartStatusTextMarginNone:
    """margin_db=None omits status line entirely."""

    def test_margin_none_omits_status(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, None)
        assert "Status" not in text
        assert "VIABLE" not in text
        assert "NOT VIABLE" not in text

    def test_margin_none_includes_loss_and_prx(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, None)
        assert "Loss: 120.0 dB" in text
        assert "Prx: -60.0 dBm" in text


class TestBuildChartStatusTextMarginZero:
    """margin_db=0 is boundary: VIABLE since >= 0."""

    def test_zero_margin_is_viable(self):
        result = types.SimpleNamespace(loss_db=130.0)
        text = build_chart_status_text(result, -70.0, 0.0)
        assert "Status: VIABLE" in text

    def test_zero_margin_includes_margin_zero(self):
        result = types.SimpleNamespace(loss_db=130.0)
        text = build_chart_status_text(result, -70.0, 0.0)
        assert "Margin: 0.0 dB" in text


class TestBuildChartStatusTextFormatting:
    """loss_db and prx_dbm are formatted to 1 decimal place."""

    def test_loss_db_one_decimal(self):
        result = types.SimpleNamespace(loss_db=123.456)
        text = build_chart_status_text(result, -60.0, 5.0)
        assert "Loss: 123.5 dB" in text

    def test_prx_dbm_one_decimal(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -65.789, 5.0)
        assert "Prx: -65.8 dBm" in text

    def test_margin_db_one_decimal(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, 3.456)
        assert "Margin: 3.5 dB" in text

    def test_loss_db_integer_still_one_decimal(self):
        result = types.SimpleNamespace(loss_db=100)
        text = build_chart_status_text(result, -50.0, 5.0)
        assert "Loss: 100.0 dB" in text

    def test_newline_structure_with_margin(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, 5.0)
        lines = text.split("\n")
        assert len(lines) == 4
        assert lines[0].startswith("Loss:")
        assert lines[1].startswith("Prx:")
        assert lines[2].startswith("Margin:")
        assert lines[3].startswith("Status:")

    def test_newline_structure_without_margin(self):
        result = types.SimpleNamespace(loss_db=120.0)
        text = build_chart_status_text(result, -60.0, None)
        lines = text.split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("Loss:")
        assert lines[1].startswith("Prx:")