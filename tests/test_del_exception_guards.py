# tests/test_del_exception_guards.py
# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression tests: __del__ exception guards for ElevationGrid and SharedDEMGrid."""



def test_elevation_grid_del_without_init(monkeypatch):
    """__del__ must not raise when __init__ was never called (AttributeError on self.data)."""
    from NoWires.elevation import ElevationGrid

    obj = ElevationGrid.__new__(ElevationGrid)
    try:
        obj.__del__()
    except (TypeError, AttributeError):
        # self.data does not exist — this is the bug
        assert False, "ElevationGrid.__del__ must not raise on uninitialized instance"


def test_elevation_grid_del_after_shutdown(monkeypatch):
    """__del__ must not raise when self.data attribute access fails during shutdown."""
    from NoWires.elevation import ElevationGrid

    obj = ElevationGrid.__new__(ElevationGrid)
    obj.data = None
    obj.__del__()


def test_shared_dem_del_without_init():
    """__del__ must not raise when self._shm was never set (AttributeError)."""
    from NoWires.shared_dem_grid import SharedDEMGrid

    obj = SharedDEMGrid.__new__(SharedDEMGrid)
    try:
        obj.__del__()
    except AttributeError:
        assert False, "SharedDEMGrid.__del__ must catch AttributeError, not just TypeError"