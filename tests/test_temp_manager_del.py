# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Tests for TempDirManager __del__ safety net and cleanup behavior."""
import logging
import os
import unittest.mock



def test_temp_manager_cleanup_removes_non_persistent_dirs():
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_cleanup")
    assert os.path.isdir(d)
    mgr.cleanup()
    assert not os.path.isdir(d)


def test_temp_manager_cleanup_removes_registered_files():
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_files")
    f = os.path.join(d, "test.txt")
    with open(f, "w") as fh:
        fh.write("test")
    mgr.add_file(f)
    assert os.path.exists(f)
    mgr.cleanup()
    assert not os.path.exists(f)


def test_temp_manager_cleanup_preserves_persistent_dirs():
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_persistent", persistent=True)
    assert os.path.isdir(d)
    mgr.cleanup()
    assert os.path.isdir(d)
    # Clean up manually
    os.rmdir(d)


def test_temp_manager_del_calls_cleanup_for_leaked_dirs():
    """__del__ should clean up non-persistent dirs if cleanup() was never called."""
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_del_leak")
    assert os.path.isdir(d)
    # Don't call cleanup() — trigger __del__ directly
    mgr.__del__()
    assert not os.path.isdir(d)


def test_temp_manager_del_no_warning_when_clean():
    """__del__ should not warn when all resources are already cleaned up."""
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_del_clean")
    mgr.cleanup()
    assert not os.path.isdir(d)
    # __del__ on already-clean manager should not warn
    logger = logging.getLogger("NoWires.temp_manager")
    with unittest.mock.patch.object(logger, "warning") as mock_warn:
        mgr.__del__()
        mock_warn.assert_not_called()


def test_temp_manager_del_cleans_up_leaked_files():
    """__del__ should clean up registered files if cleanup() was never called."""
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_del_files")
    f = os.path.join(d, "leaked.txt")
    with open(f, "w") as fh:
        fh.write("data")
    mgr.add_file(f)
    assert os.path.exists(f)
    mgr.__del__()
    assert not os.path.exists(f)


def test_temp_manager_multiple_make_dirs():
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    dirs = [mgr.make_dir(f"test_multi_{i}") for i in range(5)]
    for d in dirs:
        assert os.path.isdir(d)
    mgr.cleanup()
    for d in dirs:
        assert not os.path.isdir(d)


def test_temp_manager_warn_persistent_with_feedback():
    from NoWires.temp_manager import TempDirManager
    mgr = TempDirManager()
    d = mgr.make_dir("test_persistent_warn", persistent=True)
    feedback = unittest.mock.MagicMock()
    mgr.warn_persistent(feedback)
    feedback.pushInfo.assert_called_once()
    assert d in feedback.pushInfo.call_args[0][0]
    mgr.cleanup()
    os.rmdir(d)
