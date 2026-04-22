# -*- coding: utf-8 -*-
"""Unit tests for coverage engine execution policy and task generation."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage_engine import build_coverage_tasks, should_use_multiprocessing


def test_should_use_multiprocessing_disabled_on_windows():
    assert should_use_multiprocessing(os_name="nt") is False


def test_should_use_multiprocessing_enabled_on_non_windows():
    assert should_use_multiprocessing(os_name="posix") is True


def test_build_coverage_tasks_keeps_center_pixel_with_minimum_distance():
    tasks = build_coverage_tasks(
        tx_lat=14.0,
        tx_lon=121.0,
        radius_m=100.0,
        grid_size=3,
        profile_step_m=10.0,
        max_profile_pts=75,
        tx_h_m=30.0,
        rx_h_m=10.0,
        climate=1,
        N0=301.0,
        f_mhz=300.0,
        polarization=1,
        epsilon=15.0,
        sigma=0.005,
        time_pct=50.0,
        location_pct=50.0,
        situation_pct=50.0,
        eirp_dbm=49.0,
        rx_gain_dbi=2.0,
        antenna_az_deg=None,
        antenna_beamwidth_deg=360.0,
        lats=np.array([13.9995, 14.0, 14.0005]),
        lons=np.array([120.9995, 121.0, 121.0005]),
    )

    center_tasks = [task for task in tasks if task[0] == 1 and task[1] == 1]
    assert len(center_tasks) == 1
    assert center_tasks[0][4] == 1.0


def test_build_coverage_tasks_keeps_nearest_pixels_for_even_ui_grid_sizes():
    radius_m = 100.0
    grid_size = 64
    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / 111320.0
    lats = np.linspace(-radius_m * lat_per_m, radius_m * lat_per_m, grid_size)
    lons = np.linspace(-radius_m * lon_per_m, radius_m * lon_per_m, grid_size)

    tasks = build_coverage_tasks(
        tx_lat=0.0,
        tx_lon=0.0,
        radius_m=radius_m,
        grid_size=grid_size,
        profile_step_m=10.0,
        max_profile_pts=75,
        tx_h_m=30.0,
        rx_h_m=10.0,
        climate=1,
        N0=301.0,
        f_mhz=300.0,
        polarization=1,
        epsilon=15.0,
        sigma=0.005,
        time_pct=50.0,
        location_pct=50.0,
        situation_pct=50.0,
        eirp_dbm=49.0,
        rx_gain_dbi=2.0,
        antenna_az_deg=None,
        antenna_beamwidth_deg=360.0,
        lats=lats,
        lons=lons,
    )

    nearest_distance = min(task[4] for task in tasks)
    nearest_tasks = [task for task in tasks if abs(task[4] - nearest_distance) < 1e-9]
    assert len(nearest_tasks) == 4
    assert nearest_distance < 50.0
