# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for /dev/shm cleanup scoping (v1.5.7).

Before v1.5.7, NoWiresPlugin._cleanup_stale_shared_memory unlinked every
``/dev/shm/nowires_dem_*`` entry on plugin startup. On a shared Linux
workstation, one user's QGIS startup could destroy another user's in-flight
DEM segments. The v1.5.7 fix:

  * embeds the creator PID in the shm name (``nowires_dem_<pid>_<hex>``);
  * only unlinks entries whose PID no longer exists *and* whose ``st_uid``
    matches the calling user's effective UID;
  * leaves entries with unknown name formats alone.
"""

import os

import pytest


# Use shared_dem_grid directly — it has no qgis dependency, which keeps this
# test isolated from sys.modules["qgis.core"] pollution that other test files
# leave behind. conftest adds the plugin dir to sys.path so a top-level
# import works.
@pytest.fixture
def helper():
    from shared_dem_grid import cleanup_stale_shm_entries
    return cleanup_stale_shm_entries


@pytest.fixture
def fake_shm(tmp_path):
    return tmp_path / "shm"


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def _dead_pid():
    """Return a PID that does not correspond to any running process."""
    pid = 999999
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except OSError:
            return pid
        pid -= 1
        if pid <= 1:
            raise RuntimeError("could not find a dead PID for test")


class TestPidScoping:
    def test_live_pid_entry_is_preserved(self, helper, fake_shm):
        live_pid = os.getpid()
        target = fake_shm / "nowires_dem_{}_abcdef123".format(live_pid)
        _touch(target)
        helper(str(fake_shm), os.geteuid())
        assert target.exists(), "entry for live PID must survive cleanup"

    def test_dead_pid_entry_is_unlinked(self, helper, fake_shm):
        dead_pid = _dead_pid()
        target = fake_shm / "nowires_dem_{}_abcdef123".format(dead_pid)
        _touch(target)
        helper(str(fake_shm), os.geteuid())
        assert not target.exists(), "stale entry for dead PID must be removed"


class TestUidScoping:
    def test_mismatched_uid_entry_is_preserved(self, helper, fake_shm):
        """When my_uid != st_uid, never unlink even if PID is dead."""
        dead_pid = _dead_pid()
        target = fake_shm / "nowires_dem_{}_abcdef123".format(dead_pid)
        _touch(target)
        # Pretend the file belongs to a different user by passing a bogus my_uid.
        other_uid = os.geteuid() + 1
        helper(str(fake_shm), other_uid)
        assert target.exists(), (
            "entry owned by a different user must be left alone"
        )


class TestNameFormatScoping:
    def test_legacy_name_without_pid_is_preserved(self, helper, fake_shm):
        """Pre-v1.5.7 entries without the new <pid>_<hex> format are untouched."""
        legacy = fake_shm / "nowires_dem_abcdef0123456789"
        _touch(legacy)
        helper(str(fake_shm), os.geteuid())
        assert legacy.exists(), (
            "legacy-format entry must not be unlinked under the new scoping; "
            "we cannot prove ownership without an embedded PID"
        )

    def test_unrelated_files_are_ignored(self, helper, fake_shm):
        unrelated = fake_shm / "someone_elses_data"
        _touch(unrelated)
        helper(str(fake_shm), os.geteuid())
        assert unrelated.exists()


class TestNoShmDir:
    def test_missing_dev_shm_is_silent(self, helper, tmp_path):
        """Helper must not raise when the dir does not exist."""
        helper(str(tmp_path / "does-not-exist"), os.geteuid())  # no raise
