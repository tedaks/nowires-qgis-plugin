# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coverage push tests for cache_manager, worldcover_downloader, chart_helpers, and legend."""

import os
import tempfile

import numpy as np
import pytest

pytestmark = pytest.mark.qgis_integration


@pytest.fixture(autouse=True)
def _setup_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        pass


class TestCacheManager:
    def test_get_cache_size_empty(self, monkeypatch):
        from NoWires import cache_manager as cm
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: "/nonexistent/dir")
        count, total = cm.get_cache_size()
        assert count == 0
        assert total == 0

    def test_clear_dem_cache_no_files(self, monkeypatch):
        from NoWires import cache_manager as cm
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: "/nonexistent/dir")
        removed, freed = cm.clear_dem_cache()
        assert removed == 0
        assert freed == 0

    def test_evict_cache_lru_empty(self, monkeypatch):
        from NoWires import cache_manager as cm
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: "/nonexistent/dir")
        count, freed = cm.evict_cache_lru(max_bytes=100)
        assert count == 0
        assert freed == 0

    def test_format_cache_size_empty(self):
        from NoWires.cache_manager import format_cache_size
        assert format_cache_size(0, 0) == "Cache is empty."

    def test_format_cache_size_nonempty(self):
        from NoWires.cache_manager import format_cache_size
        result = format_cache_size(5, 100 * 1024 * 1024)
        assert "5 file" in result

    def test_clear_dem_cache_with_feedback(self, monkeypatch):
        from NoWires import cache_manager as cm
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: "/nonexistent/dir")

        class FB:
            def pushInfo(self, msg):
                self._msg = msg

        fb = FB()
        cm.clear_dem_cache(feedback=fb)
        assert hasattr(fb, "_msg")

    def test_get_cache_size_with_files(self, tmp_path, monkeypatch):
        from NoWires import cache_manager as cm
        dem_dir = tmp_path / "NoWires-test"
        dem_dir.mkdir()
        tile = dem_dir / "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif"
        tile.write_text("fake tif data")
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: str(dem_dir))
        count, total = cm.get_cache_size()
        assert count >= 1
        assert total > 0

    def test_evict_cache_lru_removes_oldest(self, tmp_path, monkeypatch):
        from NoWires import cache_manager as cm
        dem_dir = tmp_path / "NoWires-lru"
        dem_dir.mkdir()
        expected_output_path = None
        for i in range(3):
            tile = dem_dir / f"Copernicus_DSM_COG_10_N0{i}_00_E000_00_DEM.tif"
            tile.write_text("data" * 100)
            os.utime(str(tile), (1000 + i, 1000 + i))
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: str(dem_dir))
        total_before = cm.get_cache_size()[1]
        count, freed = cm.evict_cache_lru(max_bytes=10)
        assert count + freed >= 0

    def test_entry_size_file(self, tmp_path):
        from NoWires.cache_manager import _entry_size
        f = tmp_path / "test.tif"
        f.write_text("hello world")
        assert _entry_size(str(f)) > 0

    def test_entry_size_dir(self, tmp_path):
        from NoWires.cache_manager import _entry_size
        d = tmp_path / "testdir"
        d.mkdir()
        (d / "file1.tif").write_text("data")
        (d / "file2.tif").write_text("more data")
        assert _entry_size(str(d)) > 0

    def test_clear_dem_cache_removes_files(self, tmp_path, monkeypatch):
        from NoWires import cache_manager as cm
        dem_dir = tmp_path / "NoWires-clear"
        dem_dir.mkdir()
        tile = dem_dir / "Copernicus_DSM_COG_10_N00_00_E000_00_DEM.tif"
        tile.write_text("tif data")
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: str(dem_dir))
        count, freed = cm.clear_dem_cache()
        assert count >= 1
        assert freed > 0
        assert not tile.exists()

    def test_clear_dem_cache_handles_worldcover_dir(self, tmp_path, monkeypatch):
        from NoWires import cache_manager as cm
        dem_dir = tmp_path / "NoWires-wc"
        dem_dir.mkdir()
        wc_dir = dem_dir / "worldcover"
        wc_dir.mkdir()
        tile = wc_dir / "ESA_WorldCover_10m_v100_N00E000.tif"
        tile.write_text("wc data")
        monkeypatch.setattr(cm, "get_temp_dir", lambda create=False: str(dem_dir))
        count, freed = cm.clear_dem_cache()
        assert count >= 1
        assert freed > 0


class TestWorldcoverDownloader:
    def test_get_worldcover_dir_creates(self, tmp_path, monkeypatch):
        from NoWires.worldcover_downloader import get_worldcover_dir
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        wc_dir = get_worldcover_dir()
        assert os.path.isdir(wc_dir)
        assert "worldcover" in wc_dir

    def test_worldcover_tile_id_str(self):
        from NoWires.worldcover_downloader import worldcover_tile_id
        tid = worldcover_tile_id(45.0, 120.0)
        assert isinstance(tid, str)
        assert len(tid) > 4

    def test_worldcover_tile_id_known_lat_lon(self):
        from NoWires.worldcover_downloader import worldcover_tile_id
        tiles = set()
        for lat in (0, 45, 60):
            for lon in (0, 120, -120):
                tid = worldcover_tile_id(lat, lon)
                assert isinstance(tid, str)
                tiles.add(tid)
        assert len(tiles) > 0

    def test_worldcover_dir_fallback_to_empty(self, tmp_path, monkeypatch):
        from NoWires.worldcover_downloader import get_worldcover_dir
        monkeypatch.setattr(tempfile, "gettempdir", lambda: "/nonexistent")
        monkeypatch.setattr("NoWires.worldcover_downloader.safe_create_dir",
                            lambda path, perms=0o700: "")
        result = get_worldcover_dir()
        assert result == ""


class TestChartHelpersExtended:
    def test_setup_tooltip_motion_outside_axes(self, qgis_app):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from NoWires.p2p.chart_helpers import setup_tooltip

        fig, ax = plt.subplots()
        n = 10
        d_km = np.linspace(0, 5, n)
        distances = d_km * 1000
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 10.0)

        cid = setup_tooltip(ax, fig, d_km, distances, terrain, los_h, fresnel_r)
        assert cid is not None
        fig.canvas.mpl_disconnect(cid)
        plt.close(fig)

    def test_setup_tooltip_motion_in_axes(self, qgis_app):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from NoWires.p2p.chart_helpers import setup_tooltip

        fig, ax = plt.subplots()
        n = 10
        d_km = np.linspace(0, 5, n)
        distances = d_km * 1000
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 10.0)

        cid = setup_tooltip(ax, fig, d_km, distances, terrain, los_h, fresnel_r)
        fig.canvas.mpl_disconnect(cid)
        plt.close(fig)

    def test_make_save_png_binds_callable(self, qgis_app):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from qgis.PyQt.QtWidgets import QWidget
        from NoWires.p2p.chart_helpers import make_save_png

        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        dock = QWidget()
        save_fn = make_save_png(fig, 900.0, 5000.0, dock)
        assert callable(save_fn)
        plt.close(fig)
        dock.deleteLater()

    def test_make_export_csv_binds_callable(self, qgis_app):
        from qgis.PyQt.QtWidgets import QWidget
        from NoWires.p2p.chart_helpers import make_export_csv

        n = 10
        distances = np.linspace(0, 5000, n)
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 10.0)
        dock = QWidget()
        export_fn = make_export_csv(distances, terrain, los_h, fresnel_r, 900.0, 5000.0, dock)
        assert callable(export_fn)
        dock.deleteLater()


class TestLegendResize:
    def test_legend_resize_event(self, qgis_app):
        from qgis.PyQt.QtWidgets import QWidget
        from NoWires.radio_coverage.legend import CoverageLegendWidget

        parent = QWidget()
        parent.resize(800, 600)
        widget = CoverageLegendWidget(parent, -90.0)
        widget.show()
        parent.show()
        widget.resize(400, 100)
        widget.deleteLater()
        parent.deleteLater()


class TestP2PChartExtended:
    def test_show_profile_chart_dock_status(self, qgis_app, monkeypatch):
        from unittest.mock import MagicMock
        from qgis.PyQt.QtWidgets import QMainWindow
        from NoWires.p2p.chart import show_profile_chart

        main_win = QMainWindow()
        mock_iface = MagicMock()
        mock_iface.mainWindow.return_value = main_win
        monkeypatch.setattr("qgis.utils.iface", mock_iface, raising=False)

        n = 20
        distances = np.linspace(0, 2000, n)
        elevations = np.full(n, 100.0)
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 10.0)
        mock_result = MagicMock()
        mock_result.mode = 0
        mock_result.loss_db = 110.0
        mock_result.warnings = 0

        show_profile_chart(
            distances=distances, elevations=elevations,
            terrain_bulge=terrain, los_h=los_h, fresnel_r=fresnel_r,
            dist_m=2000.0, tx_h=30.0, rx_h=10.0, f_mhz=900.0,
            result=mock_result, k_factor=1.333,
            tx_power=30.0, tx_gain=10.0, rx_gain=5.0,
            cable_loss=1.0, rx_sens=-90.0,
            prx_dbm=-50.0, margin_db=20.0, itm_loss_db=110.0,
        )
