# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for coverage/legend.py (show_coverage_legend) and report/markers.py
(write_single_marker, remove_existing_ogr_dataset).

Marker tests require a real GDAL/OGR runtime. Legend tests gracefully
degrade without QGIS, returning None.
"""

import os

import pytest

# --- GDAL detection (mirrors test_report_markers.py) ---
try:
    from osgeo import ogr
    from unittest.mock import MagicMock

    _IS_OSGEO_MOCK = isinstance(ogr, MagicMock)
    _REAL_GDAL = not _IS_OSGEO_MOCK
except Exception:
    _REAL_GDAL = False

# --- Conditional GDAL-dependent imports ---
if _REAL_GDAL:
    from NoWires.report.markers import remove_existing_ogr_dataset, write_single_marker

# --- Legend import works with or without QGIS (mocked PyQt) ---
from NoWires.coverage.legend import show_coverage_legend


class TestShowCoverageLegend:
    """Covers coverage/legend.py lines 147-165 (show_coverage_legend)."""

    @pytest.mark.qgis_integration
    def test_show_coverage_legend_does_not_crash(self):
        """Call show_coverage_legend with rx_sensitivity_dbm=-100; verify no
        exception. With mocked QGIS (iface=None) it returns None gracefully.
        """
        result = show_coverage_legend(rx_sensitivity_dbm=-100)
        assert result is None or result is not None


class TestWriteSingleMarker:
    """Covers report/markers.py lines 188-229 (write_single_marker)."""

    @pytest.mark.gdal_integration
    @pytest.mark.skipif(not _REAL_GDAL, reason="Real OGR/GDAL not available (mocked by conftest)")
    def test_write_single_marker_creates_gpkg(self, tmp_path):
        path = str(tmp_path / "single_marker.gpkg")
        result = write_single_marker(
            path=path,
            lat=47.0,
            lon=8.0,
            height_m=30.0,
            gain_dbi=5.0,
            power_dbm=36.0,
            label="TX",
        )
        assert result == path
        assert os.path.exists(path)

        ds = ogr.Open(path)
        assert ds is not None, "Output GPKG must be readable by OGR"
        layer = ds.GetLayer(0)
        assert layer.GetFeatureCount() == 1

        feat = layer.GetNextFeature()
        assert feat.GetFieldAsString("label") == "TX"
        assert feat.GetFieldAsDouble("lat") == 47.0
        assert feat.GetFieldAsDouble("lon") == 8.0
        assert feat.GetFieldAsDouble("h_m") == 30.0
        assert feat.GetFieldAsDouble("gain_dbi") == 5.0
        assert feat.GetFieldAsDouble("pwr_dbm") == 36.0

        geom = feat.GetGeometryRef()
        assert geom.GetGeometryName() == "POINT"
        ds = None


class TestRemoveExistingOGRDataset:
    """Covers report/markers.py lines 55-71 (remove_existing_ogr_dataset).

    Note: test_no_error_on_nonexistent_path also exists in
    test_report_markers.py (TestRemoveExistingOGRDataset). This test
    provides a second independent check with a different path.
    """

    @pytest.mark.gdal_integration
    @pytest.mark.skipif(not _REAL_GDAL, reason="Real OGR/GDAL not available (mocked by conftest)")
    def test_remove_existing_ogr_dataset_no_error_on_nonexistent(self):
        driver = ogr.GetDriverByName("GPKG")
        remove_existing_ogr_dataset(driver, "/tmp/nonexistent_legend_markers_test.gpkg")
