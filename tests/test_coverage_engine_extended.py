# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Extended behavioral tests for coverage_engine: empty tasks, cancellation, and sequential mode."""

import numpy as np

from NoWires import coverage_engine
from NoWires import coverage_pool
from NoWires import _coverage_executor



class FakeFeedback:
    def __init__(self, cancel_after=None):
        self.messages = []
        self.progress = []
        self._cancel_after = cancel_after
        self._call_count = 0

    def pushInfo(self, msg):
        self.messages.append(msg)

    def setProgress(self, val):
        self.progress.append(val)

    def isCanceled(self):
        if self._cancel_after is not None:
            self._call_count += 1
            return self._call_count >= self._cancel_after
        return False


class FakeGrid:
    data = np.zeros((10, 10), dtype=np.float32)

    def grid_meta_dict(self):
        return {
            "min_lat": -0.01,
            "max_lat": 0.01,
            "min_lon": -0.01,
            "max_lon": 0.01,
            "n_lat": 10,
            "n_lon": 10,
            "tx_lat": 0.0,
            "tx_lon": 0.0,
        }


class TestComputeCoverageEmptyTasks:
    def test_returns_none_when_no_tasks(self, monkeypatch):
        monkeypatch.setattr(coverage_engine, "build_coverage_tasks", lambda *a, **kw: [])
        result = coverage_engine.compute_coverage(
            elev_grid=FakeGrid(),
            tx_lat=0.0, tx_lon=0.0,
            tx_h_m=30.0, rx_h_m=10.0,
            f_mhz=300.0,
            radius_km=0.001,
            grid_size=4,
        )
        assert result is None


class TestComputeCoverageCancellation:
    def test_cancel_returns_none_tuple_in_sequential_mode(self, monkeypatch):
        monkeypatch.setattr(_coverage_executor, "should_use_multiprocessing", lambda: False)

        def fake_itm_worker(task):
            return (task[0], task[1], 100.0, -50.0, 80.0, 0.0, 0.0, 0.0)

        monkeypatch.setattr(coverage_pool, "_itm_worker", fake_itm_worker)
        monkeypatch.setattr(_coverage_executor, "_itm_worker", fake_itm_worker)

        fb = FakeFeedback(cancel_after=1)
        result = coverage_engine.compute_coverage(
            elev_grid=FakeGrid(),
            tx_lat=0.0, tx_lon=0.0,
            tx_h_m=30.0, rx_h_m=10.0,
            f_mhz=300.0,
            radius_km=0.1,
            grid_size=2,
            feedback=fb,
        )
        assert result.prx_grid is None
