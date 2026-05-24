# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for shared_dem_grid, temp_manager, and nan_utils."""

import os
import tempfile

import pytest


class TestTempManagerEdges:
    def test_make_dir_persistent(self, tmp_path, monkeypatch):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        p = mgr.make_dir("test", persistent=True)
        assert os.path.isdir(p)
        assert p in mgr._persistent_dirs
        assert p not in mgr._dirs
        import shutil
        shutil.rmtree(p)

    def test_make_dir_non_persistent(self, tmp_path):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        p = mgr.make_dir("test", persistent=False)
        assert os.path.isdir(p)
        assert p in mgr._dirs
        assert p not in mgr._persistent_dirs
        mgr.cleanup()
        assert not os.path.exists(p)

    def test_add_file_and_cleanup(self, tmp_path):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        f = tmp_path / "test_file.txt"
        f.write_text("data")
        mgr.add_file(str(f))
        mgr.cleanup()
        assert not os.path.exists(str(f))

    def test_add_dir_non_persistent(self, tmp_path):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        d = tmp_path / "my_dir"
        d.mkdir()
        mgr.add_dir(str(d), persistent=False)
        assert str(d) in mgr._dirs
        mgr.cleanup()
        assert not os.path.exists(str(d))

    def test_add_dir_persistent(self, tmp_path):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        d = tmp_path / "persist_dir"
        d.mkdir()
        mgr.add_dir(str(d), persistent=True)
        assert str(d) in mgr._persistent_dirs
        mgr.cleanup()
        assert os.path.exists(str(d))
        import shutil
        shutil.rmtree(str(d))

    def test_warn_persistent_with_feedback(self, tmp_path):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        d = tmp_path / "warn_dir"
        d.mkdir()
        mgr.add_dir(str(d), persistent=True)
        fb = type("FB", (), {"pushInfo": lambda self, msg: setattr(self, "called", True)})()
        mgr.warn_persistent(feedback=fb)
        assert getattr(fb, "called", False)
        import shutil
        shutil.rmtree(str(d))

    def test_cleanup_non_existent_files_no_error(self):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        mgr.add_file("/nonexistent/path/foo.txt")
        mgr.cleanup()

    def test_double_cleanup_no_error(self, tmp_path):
        from temp_manager import TempDirManager
        mgr = TempDirManager()
        p = mgr.make_dir("double")
        mgr.cleanup()
        mgr.cleanup()
        assert not os.path.exists(p)


class TestNanUtilsSanitizers:
    def test_csv_safe_regular_value(self):
        from sanitizers import csv_safe
        assert csv_safe("hello") == "hello"
        assert csv_safe(42) == "42"

    def test_csv_safe_formula_prefix(self):
        from sanitizers import csv_safe
        assert csv_safe("=cmd|calc").startswith("'")
        assert csv_safe("+1+1").startswith("'")
        assert csv_safe("@SUM").startswith("'")
        assert csv_safe("\t=2+2").startswith("'")

    def test_csv_safe_unicode_whitespace(self):
        from sanitizers import csv_safe
        assert csv_safe("\u3000=2+2").startswith("'")

    def test_csv_safe_en_dash(self):
        from sanitizers import csv_safe
        assert csv_safe("\u2013=1").startswith("'")

    def test_csv_safe_minus_sign(self):
        from sanitizers import csv_safe
        assert csv_safe("\u22122+2").startswith("'")

    def test_sanitize_json_nan_to_none(self):
        from sanitizers import sanitize_json
        import math
        data = {"value": float("nan"), "list": [1, float("inf"), float("-inf")]}
        result = sanitize_json(data)
        assert result["value"] is None
        assert result["list"] == [1, None, None]

    def test_sanitize_json_nested_dict(self):
        from sanitizers import sanitize_json
        import math
        data = {"outer": {"inner": float("nan")}}
        result = sanitize_json(data)
        assert result["outer"]["inner"] is None


class TestCleanupStaleSharedMemory:
    def test_cleanup_nonexistent_dir(self, tmp_path):
        from shared_dem_grid import cleanup_stale_shm_entries
        cleanup_stale_shm_entries(str(tmp_path / "nonexistent"), 1000)
        assert True

    def test_cleanup_empty_dir(self, tmp_path):
        from shared_dem_grid import cleanup_stale_shm_entries
        cleanup_stale_shm_entries(str(tmp_path), os.getuid())
        assert True

    def test_cleanup_skips_non_matching_entries(self, tmp_path):
        from shared_dem_grid import cleanup_stale_shm_entries
        for name in ("other_file", "nowires_other", "nowires_dem_x_abc"):
            (tmp_path / name).write_text("")
        cleanup_stale_shm_entries(str(tmp_path), os.getuid())
        assert (tmp_path / "other_file").exists()

    def test_cleanup_removes_stale_pid(self, tmp_path, monkeypatch):
        from shared_dem_grid import cleanup_stale_shm_entries
        entry = tmp_path / "nowires_dem_99999_abc123def"
        entry.write_text("")
        cleanup_stale_shm_entries(str(tmp_path), os.getuid())
        assert not entry.exists()

    def test_atexit_release_with_empty_registry(self):
        from shared_dem_grid import _atexit_release_pending, _pending_releases
        old = dict(_pending_releases)
        _pending_releases.clear()
        try:
            _atexit_release_pending()
        finally:
            _pending_releases.update(old)
        assert True

    def test_cleanup_stale_by_uid_mismatch(self, tmp_path, monkeypatch):
        from shared_dem_grid import cleanup_stale_shm_entries
        entry = tmp_path / "nowires_dem_99998_abc123abc"
        entry.write_text("")
        cleanup_stale_shm_entries(str(tmp_path), 65534)
        assert entry.exists()

    def test_shm_name_regex_matches(self):
        import re
        from shared_dem_grid import _SHM_NAME_RE
        match = _SHM_NAME_RE.match("nowires_dem_12345_abc123def")
        assert match is not None
        assert match.group(1) == "12345"

    def test_shm_name_regex_rejects_invalid(self):
        from shared_dem_grid import _SHM_NAME_RE
        assert _SHM_NAME_RE.match("nowires_dem_x_abc") is None
        assert _SHM_NAME_RE.match("other_dem_123_abc") is None
