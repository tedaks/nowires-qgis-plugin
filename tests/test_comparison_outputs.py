# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Integration tests for comparison/outputs.py.

Tests output writing functions with synthetic raster data,
driving coverage in the comparison module.
"""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.qgis_integration


def _make_raster(path, nx=50, ny=50, value=-75.0):
    from osgeo import gdal, osr
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, nx, ny, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform([0.0, 0.01, 0, 1.0, 0, -0.01])
    data = np.full((ny, nx), value, dtype=np.float32)
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None


class TestComparisonOutputs:
    def test_write_coverage_raster(self, qgis_app, tmp_path):
        from NoWires.comparison.outputs import write_coverage_raster
        tif = str(tmp_path / "prx_a.tif")
        grid = np.full((10, 10), -80.0, dtype=np.float32)
        write_coverage_raster(tif, grid, 0.0, 1.0, 0.0, 1.0)
        assert os.path.exists(tif)

    def test_write_delta_raster(self, qgis_app, tmp_path):
        from NoWires.comparison.outputs import write_delta_raster
        tif = str(tmp_path / "delta.tif")
        grid = np.full((10, 10), 3.0, dtype=np.float32)
        write_delta_raster(tif, grid, 0.0, 1.0, 0.0, 1.0)
        assert os.path.exists(tif)

    def test_compute_delta_summary(self):
        from NoWires.comparison.outputs import compute_delta_summary
        loss_a = np.full((10, 10), 110.0, dtype=np.float32)
        loss_b = np.full((10, 10), 115.0, dtype=np.float32)
        result = compute_delta_summary(loss_a, loss_b, 3.0)
        assert result["valid_count"] == 100
        assert result["total_count"] == 100
        assert "loss_delta_grid" in result

    def test_compute_delta_summary_all_nan_b(self):
        from NoWires.comparison.outputs import compute_delta_summary
        loss_a = np.full((10, 10), 110.0, dtype=np.float32)
        loss_b = np.full((10, 10), np.nan, dtype=np.float32)
        result = compute_delta_summary(loss_a, loss_b, 3.0)
        assert result["valid_count"] == 0

    def test_write_comparison_html_report(self, tmp_path):
        from NoWires.comparison.outputs import write_comparison_html_report
        from pathlib import Path
        panel_a = {
            "tx_lat": 46.5, "tx_lon": 7.5, "tx_h": 30.0, "rx_h": 2.0,
            "f_mhz": 900.0, "radius_km": 5.0, "tx_power": 30.0,
            "tx_gain": 10.0, "rx_gain": 5.0, "cable_loss": 1.0,
            "valid_pixels": 1000, "total_pixels": 1000, "mean_prx": -75.0,
        }
        panel_b = dict(panel_a)
        delta = {
            "style": "diverging", "threshold_db": 3.0,
            "valid_pixels": 1000, "improved_pixels": 300,
            "improved_pct": 30.0, "degraded_pixels": 200,
            "degraded_pct": 20.0, "unchanged_pixels": 500,
            "unchanged_pct": 50.0,
            "min_delta": -15.0, "max_delta": 15.0, "mean_delta": 0.5,
        }
        report_path = Path(str(tmp_path / "report.html"))
        write_comparison_html_report(report_path, panel_a, panel_b, delta)
        content = report_path.read_text()
        assert "Panel A" in content
        assert "Delta Summary" in content

    def test_apply_delta_style_diverging(self, qgis_app, tmp_path):
        from NoWires.comparison.outputs import apply_delta_style
        from qgis.core import QgsRasterLayer
        tif = str(tmp_path / "style_div.tif")
        _make_raster(tif)
        layer = QgsRasterLayer(tif, "Delta Style Test")
        if layer.isValid():
            apply_delta_style(layer, 3.0, "diverging")
            assert layer.renderer() is not None

    def test_apply_delta_style_threshold(self, qgis_app, tmp_path):
        from NoWires.comparison.outputs import apply_delta_style
        from qgis.core import QgsRasterLayer
        tif = str(tmp_path / "style_thr.tif")
        _make_raster(tif)
        layer = QgsRasterLayer(tif, "Delta Threshold")
        if layer.isValid():
            apply_delta_style(layer, 3.0, "threshold")
            assert layer.renderer() is not None
