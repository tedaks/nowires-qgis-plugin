# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for temp_manager.TempDirManager."""

import os

from temp_manager import TempDirManager


class TestMakeDir:
    def test_make_dir_creates_directory(self):
        mgr = TempDirManager()
        path = mgr.make_dir("test")
        assert os.path.isdir(path)
        assert "nowires_test" in os.path.basename(path) or "nowires_" in os.path.basename(path)
        mgr.cleanup()

    def test_make_dir_persistent_creates_directory(self):
        mgr = TempDirManager()
        path = mgr.make_dir("persist", persistent=True)
        assert os.path.isdir(path)

    def test_make_dir_multiple_dirs(self):
        mgr = TempDirManager()
        a = mgr.make_dir("a")
        b = mgr.make_dir("b")
        assert os.path.isdir(a)
        assert os.path.isdir(b)
        assert a != b
        mgr.cleanup()


class TestAddFile:
    def test_add_file_removes_file_on_cleanup(self, tmp_path):
        mgr = TempDirManager()
        f = tmp_path / "deleteme.txt"
        f.write_text("hello")
        mgr.add_file(str(f))
        assert f.exists()
        mgr.cleanup()
        assert not f.exists()

    def test_add_file_missing_file_does_not_raise(self, tmp_path):
        mgr = TempDirManager()
        mgr.add_file(str(tmp_path / "nonexistent.txt"))
        mgr.cleanup()

    def test_add_file_does_not_remove_persistent_dirs(self):
        mgr = TempDirManager()
        persistent = mgr.make_dir("keep", persistent=True)
        temp = mgr.make_dir("temp")
        assert os.path.isdir(persistent)
        assert os.path.isdir(temp)
        mgr.cleanup()
        assert os.path.isdir(persistent)
        assert not os.path.isdir(temp)
        os.rmdir(persistent)


class TestAddDir:
    def test_add_dir_removes_existing_directory_on_cleanup(self, tmp_path):
        mgr = TempDirManager()
        temp_dir = tmp_path / "contourlines"
        temp_dir.mkdir()
        (temp_dir / "contourlines.shp").write_text("shape", encoding="utf-8")

        mgr.add_dir(str(temp_dir))
        mgr.cleanup()

        assert not temp_dir.exists()


class TestCleanup:
    def test_cleanup_removes_non_persistent_dirs(self):
        mgr = TempDirManager()
        path = mgr.make_dir("will_delete")
        assert os.path.isdir(path)
        mgr.cleanup()
        assert not os.path.isdir(path)

    def test_cleanup_preserves_persistent_dirs(self):
        mgr = TempDirManager()
        path = mgr.make_dir("keep", persistent=True)
        mgr.cleanup()
        assert os.path.isdir(path)
        os.rmdir(path)

    def test_cleanup_idempotent(self):
        mgr = TempDirManager()
        path = mgr.make_dir("once")
        mgr.cleanup()
        mgr.cleanup()
        assert not os.path.isdir(path)

    def test_cleanup_removes_files_in_temp_dir(self):
        mgr = TempDirManager()
        path = mgr.make_dir("withfile")
        fpath = os.path.join(path, "data.txt")
        with open(fpath, "w") as f:
            f.write("test")
        assert os.path.isfile(fpath)
        mgr.cleanup()
        assert not os.path.isdir(path)


class TestWarnPersistent:
    def test_warn_persistent_without_feedback(self):
        mgr = TempDirManager()
        path = mgr.make_dir("keep", persistent=True)
        mgr.warn_persistent()
        os.rmdir(path)

    def test_warn_persistent_with_feedback(self):
        mgr = TempDirManager()
        path = mgr.make_dir("keep", persistent=True)

        class FakeFeedback:
            def __init__(self):
                self.messages = []

            def pushInfo(self, msg):
                self.messages.append(msg)

        fb = FakeFeedback()
        mgr.warn_persistent(fb)
        assert any(path in m for m in fb.messages)
        os.rmdir(path)

    def test_warn_persistent_empty_when_no_persistent_dirs(self):
        mgr = TempDirManager()

        class FakeFeedback:
            def __init__(self):
                self.messages = []

            def pushInfo(self, msg):
                self.messages.append(msg)

        fb = FakeFeedback()
        mgr.warn_persistent(fb)
        assert fb.messages == []


class TestPrefix:
    def test_make_dir_uses_nowires_prefix(self):
        mgr = TempDirManager()
        path = mgr.make_dir("coverage_prx")
        basename = os.path.basename(path)
        assert basename.startswith("nowires_coverage_prx")
        mgr.cleanup()
