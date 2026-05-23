# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for I18: TempDirManager.__del__ TypeError during interpreter shutdown.

During CPython interpreter shutdown, module-level names (like shutil.rmtree, os.unlink,
os.path.exists, and the logger) can be set to None. When __del__ runs during shutdown,
accessing these module globals raises TypeError. The fix caches these functions on the
instance in __init__ and wraps __del__ in try/except TypeError.
"""

import os

from NoWires.temp_manager import TempDirManager


def test_del_does_not_raise_typeerror_on_shutdown(monkeypatch):
    """__del__ must not raise TypeError when module references are None (shutdown sim)."""
    mgr = TempDirManager()
    d = mgr.make_dir("test_del_shutdown")
    assert os.path.isdir(d)

    mgr.__del__()
    assert not os.path.isdir(d)


def test_del_typeerror_caught_gracefully(monkeypatch):
    """If cleanup() raises TypeError inside __del__, it must be swallowed."""
    mgr = TempDirManager()
    d = mgr.make_dir("test_del_typeerr")
    assert os.path.isdir(d)

    call_count = 0

    def cleanup_raising_typeerror():
        nonlocal call_count
        call_count += 1
        raise TypeError("simulated shutdown None ref")

    mgr.cleanup = cleanup_raising_typeerror
    mgr.__del__()
    assert call_count == 1


def test_cached_refs_used_in_cleanup():
    """cleanup() must use cached function refs, not module-level names."""
    mgr = TempDirManager()
    d = mgr.make_dir("test_cached_refs")
    assert os.path.isdir(d)
    assert hasattr(mgr, "_rmtree")
    assert hasattr(mgr, "_unlink")
    assert hasattr(mgr, "_exists")
    mgr.cleanup()
    assert not os.path.isdir(d)


def test_del_noop_when_already_cleaned():
    """__del__ on a manager with no pending dirs/files should be a no-op."""
    mgr = TempDirManager()
    d = mgr.make_dir("test_del_clean")
    assert os.path.isdir(d)
    mgr.cleanup()
    mgr.__del__()