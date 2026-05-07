# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for coverage_tasks._coverage_axis_centers and build_coverage_tasks."""

import numpy as np
import pytest

from NoWires.coverage_tasks import _coverage_axis_centers, build_coverage_tasks
from antenna import AntennaConfig
from clutter_context import ClutterLossContext


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

    def test_includes_center_pixel_with_minimum_distance(self):
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
        assert len(tasks) == 1
        assert tasks[0][4] == pytest.approx(1.0)

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
        assert len(task) == 24
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
