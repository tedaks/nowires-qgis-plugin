# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for coverage_tasks._coverage_axis_centers and build_coverage_tasks."""

import numpy as np
import pytest

from NoWires.radio_coverage.tasks import _coverage_axis_centers, _haversine_grid, _bearing_grid, build_coverage_tasks
from NoWires.antenna import AntennaConfig
from NoWires.clutter.context import ClutterLossContext


_OMNI = AntennaConfig(preset="omni")


class TestCoverageAxisCenters:
    def test_size_zero_returns_empty(self):
        result = _coverage_axis_centers(0.0, 1.0, 0)
        assert len(result) == 0

    def test_size_one_returns_midpoint(self):
        result = _coverage_axis_centers(0.0, 10.0, 1)
        assert len(result) == 1
        assert result[0] == pytest.approx(5.0)

    def test_even_spacing(self):
        result = _coverage_axis_centers(0.0, 100.0, 4)
        assert len(result) == 4
        step = 25.0
        for i in range(4):
            assert result[i] == pytest.approx(step * 0.5 + step * i)

    def test_symmetric_around_center(self):
        result = _coverage_axis_centers(-1.0, 1.0, 3)
        assert result[1] == pytest.approx(0.0)

    def test_negative_range(self):
        result = _coverage_axis_centers(-2.0, -1.0, 3)
        assert len(result) == 3
        assert result[0] < result[-1]


class TestBuildCoverageTasks:
    def test_excludes_pixels_beyond_radius(self):
        lats = np.array([14.0, 14.001, 14.002])
        lons = np.array([121.0, 121.001, 121.002])
        tasks = build_coverage_tasks(
            tx_lat=14.0, tx_lon=121.0, radius_m=10.0,
            grid_size=3, profile_step_m=10.0, max_profile_pts=75,
            tx_h_m=30.0, rx_h_m=10.0, climate=1, N0=301.0,
            f_mhz=300.0, polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            eirp_dbm=49.0, rx_gain_dbi=2.0, antenna_config=_OMNI,
            clutter_enabled=False, clutter_grid=None,
            tx_clutter_loss_db=0.0, rx_clutter_override=None,
            lats=lats, lons=lons,
        )
        for task in tasks:
            assert task[4] <= 10.0 or task[4] < 1.0

    def test_skips_near_tx_pixel(self):
        """Cells within _MIN_COVERAGE_DISTANCE_M of TX should be excluded."""
        lats = np.array([14.0])
        lons = np.array([121.0])
        tasks = build_coverage_tasks(
            tx_lat=14.0, tx_lon=121.0, radius_m=100.0,
            grid_size=1, profile_step_m=10.0, max_profile_pts=75,
            tx_h_m=30.0, rx_h_m=10.0, climate=1, N0=301.0,
            f_mhz=300.0, polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            eirp_dbm=49.0, rx_gain_dbi=2.0, antenna_config=_OMNI,
            clutter_enabled=False, clutter_grid=None,
            tx_clutter_loss_db=0.0, rx_clutter_override=None,
            lats=lats, lons=lons,
        )
        # Cell at exact TX location has d_m ≈ 0 < _MIN_COVERAGE_DISTANCE_M
        assert len(tasks) == 0

    def test_task_tuple_contains_correct_fields(self):
        lats = np.array([14.0, 14.001])
        lons = np.array([121.0, 121.001])
        tasks = build_coverage_tasks(
            tx_lat=14.0, tx_lon=121.0, radius_m=100000.0,
            grid_size=2, profile_step_m=10.0, max_profile_pts=75,
            tx_h_m=30.0, rx_h_m=10.0, climate=1, N0=301.0,
            f_mhz=300.0, polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            eirp_dbm=49.0, rx_gain_dbi=2.0, antenna_config=_OMNI,
            clutter_enabled=False, clutter_grid=None,
            tx_clutter_loss_db=0.0, rx_clutter_override=None,
            lats=lats, lons=lons,
        )
        assert len(tasks) >= 1
        task = tasks[0]
        assert len(task) == 25
        i, j = task[0], task[1]
        assert 0 <= i < 2
        assert 0 <= j < 2
        assert isinstance(task[2], float)
        assert isinstance(task[3], float)

    def test_num_profile_points_respected(self):
        lats = np.array([14.0])
        lons = np.array([121.001])
        tasks = build_coverage_tasks(
            tx_lat=14.0, tx_lon=121.0, radius_m=100000.0,
            grid_size=1, profile_step_m=10.0, max_profile_pts=8,
            tx_h_m=30.0, rx_h_m=10.0, climate=1, N0=301.0,
            f_mhz=300.0, polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            eirp_dbm=49.0, rx_gain_dbi=2.0, antenna_config=_OMNI,
            clutter_enabled=False, clutter_grid=None,
            tx_clutter_loss_db=0.0, rx_clutter_override=None,
            lats=lats, lons=lons,
        )
        assert len(tasks) == 1
        n_pts = tasks[0][7]
        assert n_pts <= 8

    def test_clutter_disabled_uses_open_category(self):
        lats = np.array([14.0])
        lons = np.array([121.001])
        tasks = build_coverage_tasks(
            tx_lat=14.0, tx_lon=121.0, radius_m=100000.0,
            grid_size=1, profile_step_m=10.0, max_profile_pts=75,
            tx_h_m=30.0, rx_h_m=10.0, climate=1, N0=301.0,
            f_mhz=300.0, polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            eirp_dbm=49.0, rx_gain_dbi=2.0, antenna_config=_OMNI,
            clutter_enabled=False, clutter_grid=None,
            tx_clutter_loss_db=0.0, rx_clutter_override=None,
            lats=lats, lons=lons,
        )
        assert len(tasks) == 1
        assert tasks[0][23] == 0.0

    def test_advanced_mode_uses_overrides_without_raster(self):
        lats = np.array([14.0])
        lons = np.array([121.01])
        ctx = ClutterLossContext(
            frequency_mhz=1800.0,
            distance_m=0.0,
            tx_height_m=2.0,
            rx_height_m=2.0,
            polarization=1,
            model="advanced",
        )

        tasks = build_coverage_tasks(
            tx_lat=14.0, tx_lon=121.0, radius_m=100000.0,
            grid_size=1, profile_step_m=10.0, max_profile_pts=75,
            tx_h_m=2.0, rx_h_m=2.0, climate=1, N0=301.0,
            f_mhz=1800.0, polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            eirp_dbm=49.0, rx_gain_dbi=2.0, antenna_config=_OMNI,
            clutter_enabled=True, clutter_grid=None,
            tx_clutter_loss_db=0.0, rx_clutter_override="urban",
            lats=lats, lons=lons, clutter_context=ctx,
            tx_clutter_override="urban",
        )

        assert len(tasks) == 1
        assert tasks[0].clutter_tx_db > 0.0
        assert tasks[0].clutter_rx_db > 0.0


class TestHaversineGrid:
    def test_same_point_zero_distance(self):
        lats = np.array([14.0])
        lons = np.array([121.0])
        dist = _haversine_grid(14.0, 121.0, lats, lons)
        assert dist[0, 0] == pytest.approx(0.0, abs=1.0)

    def test_known_distance_paris_london(self):
        lats = np.array([51.5074])
        lons = np.array([-0.1278])
        dist = _haversine_grid(48.8566, 2.3522, lats, lons)
        assert dist[0, 0] == pytest.approx(343000.0, rel=0.02)

    def test_grid_shape_matches_lats_lons(self):
        lats = np.array([14.0, 14.01, 14.02])
        lons = np.array([121.0, 121.01, 121.02, 121.03])
        dist = _haversine_grid(14.0, 121.0, lats, lons)
        assert dist.shape == (3, 4)

    def test_symmetry(self):
        lats = np.array([14.01])
        lons = np.array([121.01])
        d1 = _haversine_grid(14.0, 121.0, lats, lons)[0, 0]
        d2 = _haversine_grid(14.01, 121.01, np.array([14.0]), np.array([121.0]))[0, 0]
        assert d1 == pytest.approx(d2, rel=1e-10)


class TestBearingGrid:
    def test_due_north(self):
        lats = np.array([15.0])
        lons = np.array([121.0])
        bearing = _bearing_grid(14.0, 121.0, lats, lons)
        assert bearing[0, 0] == pytest.approx(0.0, abs=1.0)

    def test_due_south(self):
        lats = np.array([13.0])
        lons = np.array([121.0])
        bearing = _bearing_grid(14.0, 121.0, lats, lons)
        assert bearing[0, 0] == pytest.approx(180.0, abs=1.0)

    def test_due_east(self):
        lats = np.array([0.0])
        lons = np.array([1.0])
        bearing = _bearing_grid(0.0, 0.0, lats, lons)
        assert bearing[0, 0] == pytest.approx(90.0, abs=1.0)

    def test_bearing_range_0_360(self):
        lats = np.array([0.0, 0.0, 0.0])
        lons = np.array([1.0, -1.0, 179.0])
        bearings = _bearing_grid(0.0, 0.0, lats, lons)
        for b in bearings[0]:
            assert 0.0 <= b <= 360.0
