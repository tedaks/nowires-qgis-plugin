# -*- coding: utf-8 -*-
"""Unit tests for coverage engine execution policy and task generation."""

import numpy as np

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


def test_compute_coverage_samples_cell_centers_within_requested_extent(monkeypatch):
    import coverage_engine

    captured = {}

    def fake_build_coverage_tasks(*args, **kwargs):
        captured["lats"] = args[-2].copy()
        captured["lons"] = args[-1].copy()
        return []

    monkeypatch.setattr(coverage_engine, "build_coverage_tasks", fake_build_coverage_tasks)

    class _DummyGrid:
        data = np.zeros((2, 2), dtype=np.float32)

        @staticmethod
        def grid_meta_dict():
            return {
                "min_lat": -0.001,
                "max_lat": 0.001,
                "min_lon": -0.001,
                "max_lon": 0.001,
                "n_lat": 2,
                "n_lon": 2,
            }

    coverage_engine.compute_coverage(
        elev_grid=_DummyGrid(),
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=300.0,
        radius_km=0.1,
        grid_size=4,
    )

    radius_m = 100.0
    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / 111320.0
    half_lat = radius_m * lat_per_m
    half_lon = radius_m * lon_per_m
    lat_step = (half_lat * 2.0) / 4.0
    lon_step = (half_lon * 2.0) / 4.0

    expected_lats = np.array(
        [
            -half_lat + (lat_step * 0.5),
            -half_lat + (lat_step * 1.5),
            -half_lat + (lat_step * 2.5),
            -half_lat + (lat_step * 3.5),
        ]
    )
    expected_lons = np.array(
        [
            -half_lon + (lon_step * 0.5),
            -half_lon + (lon_step * 1.5),
            -half_lon + (lon_step * 2.5),
            -half_lon + (lon_step * 3.5),
        ]
    )

    assert np.allclose(captured["lats"], expected_lats)
    assert np.allclose(captured["lons"], expected_lons)
