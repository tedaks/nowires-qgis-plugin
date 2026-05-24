# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test for dem_downloader.get_temp_dir() TOCTOU race (v1.6.2).

Before the fix, get_temp_dir() used os.makedirs(target, exist_ok=True) for
initial directory creation, which has a symlink-following window between the
permission check and the actual creation. The fix replaces os.makedirs with
the atomic tempfile.mkdtemp() + os.rename() pattern already used by
worldcover_downloader._safe_create_dir.
"""

import os
import stat as stat_module
import tempfile
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _patch_env():
    """Stable username and temp dir; unbuffered logging to avoid recursion."""
    with mock.patch("NoWires.dem_downloader.getpass.getuser", return_value="testuser"):
        with mock.patch("NoWires.dem_downloader.tempfile.gettempdir", return_value="/tmp"):
            yield


def test_uses_mkdtemp_rename_not_makedirs():
    """When target is missing, mkdtemp+rename is used instead of os.makedirs."""
    os_makedirs = mock.Mock()
    os_lstat = mock.Mock(side_effect=OSError("no such file"))
    os_stat = mock.Mock(return_value=mock.Mock(st_mode=0o40700))
    os_chmod = mock.Mock()
    os_rename = mock.Mock(side_effect=lambda src, dst: None)
    mkdtemp_fn = mock.Mock(return_value="/tmp/mkdtemp_abc123")
    path_isdir = mock.Mock(return_value=False)
    path_dirname = mock.Mock(return_value="/tmp")

    with mock.patch.multiple(
        "NoWires.dem_downloader.os",
        makedirs=os_makedirs,
        lstat=os_lstat,
        stat=os_stat,
        chmod=os_chmod,
        rename=os_rename,
    ), mock.patch.object(
        os.path, "isdir", path_isdir
    ), mock.patch.object(
        os.path, "dirname", path_dirname
    ), mock.patch.object(
        tempfile, "mkdtemp", mkdtemp_fn
    ):
        from NoWires.dem_downloader import get_temp_dir
        result = get_temp_dir()

    os_makedirs.assert_not_called()
    mkdtemp_fn.assert_called_once()
    os_rename.assert_called_once()
    assert result is not None


def test_mkdtemp_rename_is_not_fallback_only():
    """mkdtemp+rename is the primary creation path, not an OSError fallback."""
    mkdtemp_fn = mock.Mock(return_value="/tmp/primary_abc")
    os_makedirs = mock.Mock()
    os_rename = mock.Mock(side_effect=lambda src, dst: None)

    with mock.patch.multiple(
        "NoWires.dem_downloader.os",
        makedirs=os_makedirs,
        lstat=mock.Mock(side_effect=OSError("no such file")),
        stat=mock.Mock(return_value=mock.Mock(st_mode=0o40700)),
        chmod=mock.Mock(),
        rename=os_rename,
    ), mock.patch.object(
        os.path, "isdir", return_value=False
    ), mock.patch.object(
        os.path, "dirname", return_value="/tmp"
    ), mock.patch.object(
        tempfile, "mkdtemp", mkdtemp_fn
    ):
        from NoWires.dem_downloader import get_temp_dir
        get_temp_dir()

    os_makedirs.assert_not_called()
    mkdtemp_fn.assert_called_once()


def test_existing_valid_dir_no_creation_calls():
    """When target is already a valid directory, no mkdtemp or makedirs."""
    st = mock.Mock(spec=["st_mode"])
    st.st_mode = stat_module.S_IFDIR
    mkdtemp_fn = mock.Mock()
    os_makedirs = mock.Mock()

    with mock.patch.multiple(
        "NoWires.dem_downloader.os",
        makedirs=os_makedirs,
        lstat=mock.Mock(return_value=st),
        stat=mock.Mock(return_value=mock.Mock(st_mode=0o40700)),
        chmod=mock.Mock(),
    ), mock.patch.object(
        os.path, "isdir", return_value=True
    ), mock.patch.object(
        os.path, "dirname", return_value="/tmp"
    ), mock.patch.object(
        tempfile, "mkdtemp", mkdtemp_fn
    ):
        from NoWires.dem_downloader import get_temp_dir
        get_temp_dir()

    os_makedirs.assert_not_called()
    mkdtemp_fn.assert_not_called()


def test_symlink_removed_then_mkdtemp_used():
    """Symlink at target is unlinked, then mkdtemp+rename replaces it."""
    st = mock.Mock(spec=["st_mode"])
    st.st_mode = stat_module.S_IFLNK
    os_unlink = mock.Mock()
    os_rename = mock.Mock(side_effect=lambda src, dst: None)
    mkdtemp_fn = mock.Mock(return_value="/tmp/newdir_xyz")
    os_makedirs = mock.Mock()

    with mock.patch.multiple(
        "NoWires.dem_downloader.os",
        makedirs=os_makedirs,
        lstat=mock.Mock(return_value=st),
        stat=mock.Mock(return_value=mock.Mock(st_mode=0o40700)),
        chmod=mock.Mock(),
        unlink=os_unlink,
        rename=os_rename,
    ), mock.patch.object(
        os.path, "isdir", side_effect=[False]
    ), mock.patch.object(
        os.path, "dirname", return_value="/tmp"
    ), mock.patch.object(
        tempfile, "mkdtemp", mkdtemp_fn
    ):
        from NoWires.dem_downloader import get_temp_dir
        get_temp_dir()

    os_unlink.assert_called_once()
    os_makedirs.assert_not_called()
    mkdtemp_fn.assert_called_once()
