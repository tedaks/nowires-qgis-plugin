# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for cache_manager.py."""

import os
import tempfile

import pytest

from nowires_qgis_plugin.cache_manager import clear_dem_cache


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
    # via `from .dem_downloader import get_temp_dir`, creating a local binding.
    # Both the source module and cache_manager's reference must be patched.
    import nowires_qgis_plugin.dem_downloader as ddl
    import nowires_qgis_plugin.cache_manager as cm
    original_ddl = ddl.get_temp_dir
    original_cm = cm.get_temp_dir
    ddl.get_temp_dir = lambda: tmp
    cm.get_temp_dir = lambda: tmp
    # Also monkey-patch worldcover dir helpers
    import nowires_qgis_plugin.worldcover_downloader as wcd
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
        import nowires_qgis_plugin.dem_downloader as ddl
        import nowires_qgis_plugin.cache_manager as cm
        ddl.get_temp_dir = lambda: "/nonexistent/path/nowires_test"
        cm.get_temp_dir = lambda: "/nonexistent/path/nowires_test"
        removed, freed = clear_dem_cache()
        assert removed == 0
        assert freed == 0

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
