# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: TempDirManager.__del__ must not raise on uninitialized instance."""


def test_temp_manager_del_without_init():
    """__del__ must not raise when __init__ was never called (AttributeError on self._dirs)."""
    from NoWires.temp_manager import TempDirManager

    obj = TempDirManager.__new__(TempDirManager)
    try:
        obj.__del__()
    except AttributeError:
        assert False, "TempDirManager.__del__ must not raise on uninitialized instance"


def test_temp_manager_del_after_partial_init():
    """__del__ must not raise when only some attributes are set."""
    from NoWires.temp_manager import TempDirManager

    obj = TempDirManager.__new__(TempDirManager)
    obj._dirs = []
    try:
        obj.__del__()
    except AttributeError:
        assert False, "TempDirManager.__del__ must not raise with partial init"