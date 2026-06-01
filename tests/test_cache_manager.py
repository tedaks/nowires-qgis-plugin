# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for cache_manager.py."""

import os
import shutil
import tempfile
from unittest import mock

import pytest

from cache_manager import (
    _entry_size,  # noqa: F401
    _iter_cache_entries,  # noqa: F401
    clear_dem_cache,
    format_cache_size,
    get_cache_size,
)


class _FeedbackStub:
    """Minimal feedback stub that records pushInfo calls."""

    def __init__(self):
        self.messages = []

    def pushInfo(self, msg):
        self.messages.append(msg)


@pytest.fixture
def temp_cache_dir():
    """Create an isolated temp directory and point get_temp_dir at it."""
    tmp = tempfile.mkdtemp(prefix="nowires_test_cache_")
    # Monkey-patch dem_downloader.get_temp_dir — cache_manager imports this
    # via `from NoWires.dem_downloader import get_temp_dir`, creating a local binding.
    # Both the source module and cache_manager's reference must be patched.
    import dem_downloader as ddl
    import cache_manager as cm
    original_ddl = ddl.get_temp_dir
    original_cm = cm.get_temp_dir
    ddl.get_temp_dir = lambda create=True: tmp
    cm.get_temp_dir = lambda create=True: tmp
    # Also monkey-patch worldcover dir helpers
    import worldcover_downloader as wcd
    original_wc = wcd.get_worldcover_dir
    wcd_dir = os.path.join(tmp, "worldcover")
    os.makedirs(wcd_dir, exist_ok=True)
    wcd.get_worldcover_dir = lambda: wcd_dir
    yield tmp
    ddl.get_temp_dir = original_ddl
    cm.get_temp_dir = original_cm
    wcd.get_worldcover_dir = original_wc
    # Clean up
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestClearDemCache:
    """Tests for clear_dem_cache()."""

    def test_empty_directory(self, temp_cache_dir):
        """No files removed when cache dir is empty."""
        removed, freed = clear_dem_cache()
        assert removed == 0
        assert freed == 0

    def test_non_existent_directory(self):
        """Gracefully handles missing temp directory."""
        import dem_downloader as ddl
        import cache_manager as cm
        original_ddl = ddl.get_temp_dir
        original_cm = cm.get_temp_dir
        try:
            ddl.get_temp_dir = lambda create=True: "/nonexistent/path/nowires_test"
            cm.get_temp_dir = lambda create=True: "/nonexistent/path/nowires_test"
            removed, freed = clear_dem_cache()
            assert removed == 0
            assert freed == 0
        finally:
            ddl.get_temp_dir = original_ddl
            cm.get_temp_dir = original_cm

    def test_removes_glo30_tiles(self, temp_cache_dir):
        """GLO-30 tile files are removed."""
        tile_path = os.path.join(temp_cache_dir, "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif")
        with open(tile_path, "w") as f:
            f.write("dummy tile data" * 100)
        size = os.path.getsize(tile_path)

        removed, freed = clear_dem_cache()
        assert removed == 1
        assert freed >= size
        assert not os.path.exists(tile_path)

    def test_removes_merged_dem(self, temp_cache_dir):
        """Merged DEM files are removed."""
        merged = os.path.join(temp_cache_dir, "merged_dem.tif")
        with open(merged, "w") as f:
            f.write("merged data" * 200)
        size = os.path.getsize(merged)

        removed, freed = clear_dem_cache()
        assert removed == 1
        assert freed >= size
        assert not os.path.exists(merged)

    def test_removes_worldcover_tiles(self, temp_cache_dir):
        """WorldCover tiles in subdirectory are removed."""
        wc_dir = os.path.join(temp_cache_dir, "worldcover")
        os.makedirs(wc_dir, exist_ok=True)
        wc_tile = os.path.join(wc_dir, "ESA_WorldCover_10m_2020_v100_N00E000_Map.tif")
        with open(wc_tile, "w") as f:
            f.write("worldcover data" * 100)
        size = os.path.getsize(wc_tile)

        removed, freed = clear_dem_cache()
        assert removed == 1
        assert freed >= size
        assert not os.path.exists(wc_tile)

    def test_removes_merged_worldcover(self, temp_cache_dir):
        """Merged WorldCover files in subdirectory are removed."""
        wc_dir = os.path.join(temp_cache_dir, "worldcover")
        os.makedirs(wc_dir, exist_ok=True)
        merged_wc = os.path.join(wc_dir, "merged_worldcover.tif")
        with open(merged_wc, "w") as f:
            f.write("merged wc data" * 100)
        size = os.path.getsize(merged_wc)

        removed, freed = clear_dem_cache()
        assert removed == 1
        assert freed >= size
        assert not os.path.exists(merged_wc)

    def test_handles_readonly_files(self, temp_cache_dir):
        """Does not crash on read-only files or permission errors."""
        tile_path = os.path.join(temp_cache_dir, "Copernicus_DSM_COG_10_N01_00_E001_00_DEM.tif")
        with open(tile_path, "w") as f:
            f.write("data")
        os.chmod(tile_path, 0o444)  # read-only - os.unlink can still succeed on Linux
        removed, _ = clear_dem_cache()
        assert removed >= 0  # should not crash

    def test_feedback_integration(self, temp_cache_dir):
        """Feedback object receives pushInfo with summary."""
        tile_path = os.path.join(temp_cache_dir, "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif")
        with open(tile_path, "w") as f:
            f.write("data" * 500)
        fb = _FeedbackStub()
        removed, freed = clear_dem_cache(feedback=fb)
        assert removed == 1
        assert len(fb.messages) == 1
        assert "removed 1" in fb.messages[0] or "removed" in fb.messages[0].lower()

    def test_no_feedback_crash(self, temp_cache_dir):
        """clear_dem_cache() works fine with feedback=None (default)."""
        removed, freed = clear_dem_cache()
        assert removed >= 0
        assert freed >= 0


class TestGetCacheSize:
    """Tests for get_cache_size() and format_cache_size()."""

    def test_empty_cache_returns_zero(self, temp_cache_dir):
        count, total = get_cache_size()
        assert count == 0
        assert total == 0

    def test_counts_dem_and_worldcover(self, temp_cache_dir):
        tile = os.path.join(
            temp_cache_dir, "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif")
        with open(tile, "w") as f:
            f.write("d" * 1234)
        wc_dir = os.path.join(temp_cache_dir, "worldcover")
        os.makedirs(wc_dir, exist_ok=True)
        wc_tile = os.path.join(wc_dir, "ESA_WorldCover_10m_2020_v100_N00E000_Map.tif")
        with open(wc_tile, "w") as f:
            f.write("w" * 4321)
        count, total = get_cache_size()
        assert count == 2
        assert total == 1234 + 4321

    def test_format_empty(self):
        assert format_cache_size(0, 0) == "Cache is empty."

    def test_format_nonempty(self):
        msg = format_cache_size(3, 2 * 1048576)
        assert "3 file" in msg
        assert "2.0 MB" in msg

    def test_does_not_remove_files(self, temp_cache_dir):
        tile = os.path.join(temp_cache_dir, "merged_dem.tif")
        with open(tile, "w") as f:
            f.write("data")
        get_cache_size()
        assert os.path.exists(tile)


class TestGetCacheSizeOserrors:
    """Tests for OSError suppression in get_cache_size()."""

    def test_get_cache_size_oserror_suppressed(self):
        """OSError from _entry_size during get_cache_size is caught, returns (0, 0)."""
        tmp = tempfile.mkdtemp(prefix="nowires_test_oserror_")
        try:
            fake_entry = os.path.join(tmp, "nowires_dem_test.tif")
            with open(fake_entry, "w") as f:
                f.write("data")

            import NoWires.dem_downloader as ddl_mod
            import NoWires.cache_manager as cm_mod
            orig_ddl = ddl_mod.get_temp_dir
            orig_cm = cm_mod.get_temp_dir
            ddl_mod.get_temp_dir = lambda create=True: tmp
            cm_mod.get_temp_dir = lambda create=True: tmp
            try:
                with mock.patch(
                    "NoWires.cache_manager._entry_size",
                    side_effect=OSError("permission denied"),
                ):
                    count, total = get_cache_size()
                assert count == 0
                assert total == 0
            finally:
                ddl_mod.get_temp_dir = orig_ddl
                cm_mod.get_temp_dir = orig_cm
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_get_cache_size_empty_temp_dir(self):
        """get_cache_size returns (0, 0) when temp dir does not exist."""
        with mock.patch(
            "NoWires.dem_downloader.get_temp_dir",
            return_value="/nonexistent/path/for/test",
        ):
            with mock.patch(
                "NoWires.cache_manager.get_temp_dir",
                return_value="/nonexistent/path/for/test",
            ):
                count, total = get_cache_size()
        assert count == 0
        assert total == 0


class TestClearDemCacheEdgeCases:
    """Tests for edge cases in clear_dem_cache()."""

    def test_clear_dem_cache_removes_directory(self):
        """Removes directory entries via shutil.rmtree."""
        tmp = tempfile.mkdtemp(prefix="nowires_test_dir_")
        try:
            subdir = os.path.join(tmp, "nowires_dem_testdir")
            os.mkdir(subdir)
            fpath = os.path.join(subdir, "file.txt")
            with open(fpath, "w") as f:
                f.write("some data" * 100)
            file_size = os.path.getsize(fpath)

            with mock.patch(
                "NoWires.cache_manager._iter_cache_entries",
                return_value=iter([subdir]),
            ):
                removed, freed = clear_dem_cache()

            assert removed == 1
            assert freed >= file_size
            assert not os.path.exists(subdir)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_clear_dem_cache_with_feedback(self):
        """feedback.pushInfo is called with cache removal summary."""
        fb = mock.MagicMock()
        with mock.patch(
            "NoWires.cache_manager._iter_cache_entries",
            return_value=iter([]),
        ):
            removed, freed = clear_dem_cache(feedback=fb)
        assert removed == 0
        assert freed == 0
        fb.pushInfo.assert_called_once()
        msg = fb.pushInfo.call_args[0][0]
        assert "removed" in msg

    def test_clear_dem_cache_oserror_suppressed(self):
        """OSError during _entry_size in clear_dem_cache is caught; partial counts returned."""
        tmp = tempfile.mkdtemp(prefix="nowires_test_ose_")
        try:
            good_file = os.path.join(tmp, "nowires_dem_good.tif")
            bad_file = os.path.join(tmp, "nowires_dem_bad.tif")
            with open(good_file, "w") as f:
                f.write("good" * 100)
            good_size = os.path.getsize(good_file)
            with open(bad_file, "w") as f:
                f.write("bad" * 100)

            with mock.patch(
                "NoWires.cache_manager._iter_cache_entries",
                return_value=iter([good_file, bad_file]),
            ):
                with mock.patch(
                    "NoWires.cache_manager._entry_size",
                    side_effect=[good_size, OSError("permission denied")],
                ):
                    removed, freed = clear_dem_cache()

            assert removed == 1
            assert freed >= good_size
            assert os.path.exists(bad_file)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFormatCacheSizeEdgeCases:
    """Tests for format_cache_size() covering edge cases."""

    def test_format_cache_size_empty(self):
        """format_cache_size(0, 0) returns 'Cache is empty.'"""
        assert format_cache_size(0, 0) == "Cache is empty."

    def test_format_cache_size_non_empty(self):
        """format_cache_size(5, 1048576) returns string with file count and size."""
        msg = format_cache_size(5, 1048576)
        assert "5 file(s)" in msg
        assert "1.0 MB" in msg
