# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Full algorithm processAlgorithm integration tests for Docker QGIS."""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.qgis_integration

from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsPointXY


@pytest.fixture(scope="module")
def synthetic_dem_path(tmp_path_factory):
    from osgeo import gdal, osr
    path = tmp_path_factory.mktemp("dem") / "synthetic.tif"
    nx, ny = 200, 200
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), nx, ny, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetProjection(srs.ExportToWkt())
    south, north = 46.0, 47.0
    west, east = 7.0, 8.0
    dx = (east - west) / nx
    dy = (north - south) / ny
    ds.SetGeoTransform([west, dx, 0, north, 0, -dy])
    data = np.full((ny, nx), 200.0, dtype=np.float32)
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None
    return str(path)


@pytest.fixture(autouse=True)
def _patch_dem(monkeypatch, synthetic_dem_path):
    from NoWires import dem_downloader
    monkeypatch.setattr(dem_downloader, "ensure_dem_for_area",
                        lambda *a, **kw: synthetic_dem_path)


class Feedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.messages = []
    def pushInfo(self, msg): self.messages.append(msg)
    def pushWarning(self, msg): self.messages.append(msg)


class TestP2PAlgorithmExecution:
    def test_p2p_algorithm_creates_outputs(self, qgis_app, tmp_path):
        from NoWires.algorithm.p2p import P2PAlgorithm

        alg = P2PAlgorithm()
        alg.initAlgorithm({})
        context = QgsProcessingContext()
        feedback = Feedback()

        params = {
            "TX_POINT": QgsPointXY(7.4, 46.5),
            "RX_POINT": QgsPointXY(7.6, 46.5),
            "FREQ_MHZ": 900.0, "TX_HEIGHT": 30.0, "RX_HEIGHT": 10.0,
            "POLARIZATION": 0, "CLIMATE": 0,
            "TX_POWER": 30.0, "TX_GAIN": 10.0, "RX_GAIN": 5.0,
            "CABLE_LOSS": 1.0, "RX_SENSITIVITY": -90.0,
            "K_FACTOR_PRESET": 0,
            "TIME_PCT": 50.0, "LOCATION_PCT": 50.0, "SITUATION_PCT": 50.0,
            "ANTENNA_BW": 360.0, "ANTENNA_AZ": 0.0, "ANTENNA_PRESET": 0,
            "FRONT_BACK_DB": 25.0, "DOWNTILT_DEG": 0.0,
            "H_PATTERN": "", "V_PATTERN": "",
            "CLUTTER_MODEL": 0, "CLUTTER_RASTER": "",
            "TX_CLUTTER_OVERRIDE": None, "RX_CLUTTER_OVERRIDE": None,
            "PROFILE_DEST": str(tmp_path / "profile.shp"),
            "FRESNEL_DEST": str(tmp_path / "fresnel.shp"),
            "MARKERS_DEST": str(tmp_path / "markers.shp"),
            "REPORT_CSV": str(tmp_path / "report.csv"),
            "REPORT_JSON": str(tmp_path / "report.json"),
            "REPORT_HTML": "", "SHOW_CHART": False,
        }
        result = alg.processAlgorithm(params, context, feedback)
        assert result is not None
        assert len(result) > 0


class TestCoverageAlgorithmExecution:
    def test_coverage_algorithm_creates_raster(self, qgis_app, tmp_path):
        from NoWires.algorithm.coverage import CoverageAlgorithm

        alg = CoverageAlgorithm()
        alg.initAlgorithm({})
        context = QgsProcessingContext()
        feedback = Feedback()

        params = {
            "TX_POINT": QgsPointXY(7.5, 46.5),
            "FREQ_MHZ": 900.0, "TX_HEIGHT": 30.0, "RX_HEIGHT": 2.0,
            "RADIUS_KM": 5.0, "GRID_SIZE": 0,
            "POLARIZATION": 0, "CLIMATE": 0,
            "TX_POWER": 30.0, "TX_GAIN": 10.0, "RX_GAIN": 5.0,
            "CABLE_LOSS": 1.0, "RX_SENSITIVITY": -90.0,
            "K_FACTOR_PRESET": 0,
            "TIME_PCT": 50.0, "LOCATION_PCT": 50.0, "SITUATION_PCT": 50.0,
            "ANTENNA_BW": 360.0, "ANTENNA_AZ": 0.0, "ANTENNA_PRESET": 0,
            "FRONT_BACK_DB": 25.0, "DOWNTILT_DEG": 0.0,
            "H_PATTERN": "", "V_PATTERN": "",
            "CLUTTER_MODEL": 0, "CLUTTER_RASTER": "",
            "TX_CLUTTER_OVERRIDE": None, "RX_CLUTTER_OVERRIDE": None,
            "OUTPUT_PRX": str(tmp_path / "prx.tif"),
            "OUTPUT_REPORT_CSV": "", "OUTPUT_REPORT_JSON": "",
            "OUTPUT_REPORT_HTML": "", "OUTPUT_REPORT_PDF": "",
            "SHOW_LEGEND": False,
        }
        result = alg.processAlgorithm(params, context, feedback)
        assert result is not None
        for key in result:
            path = result[key]
            if isinstance(path, str) and path.endswith(".tif"):
                assert os.path.exists(path), f"Missing output: {path}"


class TestComparisonAlgorithmExecution:
    def test_comparison_algorithm_creates_delta(self, qgis_app, tmp_path):
        from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm

        alg = CoverageComparisonAlgorithm()
        alg.initAlgorithm({})
        context = QgsProcessingContext()
        feedback = Feedback()

        base = str(tmp_path)
        tx = QgsPointXY(7.5, 46.5)
        params = {
            "PANEL_A_POINT": tx, "PANEL_B_POINT": tx,
            "PANEL_A_FREQ_MHZ": 900.0, "PANEL_B_FREQ_MHZ": 900.0,
            "PANEL_A_TX_HEIGHT": 30.0, "PANEL_B_TX_HEIGHT": 30.0,
            "PANEL_A_RX_HEIGHT": 2.0, "PANEL_B_RX_HEIGHT": 2.0,
            "PANEL_A_RADIUS_KM": 3.0, "PANEL_B_RADIUS_KM": 3.0,
            "PANEL_A_GRID_SIZE": 0, "PANEL_B_GRID_SIZE": 0,
            "PANEL_A_POLARIZATION": 0, "PANEL_B_POLARIZATION": 0,
            "PANEL_A_CLIMATE": 0, "PANEL_B_CLIMATE": 0,
            "PANEL_A_TX_POWER": 30.0, "PANEL_B_TX_POWER": 30.0,
            "PANEL_A_TX_GAIN": 10.0, "PANEL_B_TX_GAIN": 10.0,
            "PANEL_A_RX_GAIN": 5.0, "PANEL_B_RX_GAIN": 5.0,
            "PANEL_A_CABLE_LOSS": 1.0, "PANEL_B_CABLE_LOSS": 1.0,
            "PANEL_A_RX_SENSITIVITY": -90.0, "PANEL_B_RX_SENSITIVITY": -90.0,
            "PANEL_A_TIME_PCT": 50.0, "PANEL_B_TIME_PCT": 50.0,
            "PANEL_A_LOCATION_PCT": 50.0, "PANEL_B_LOCATION_PCT": 50.0,
            "PANEL_A_SITUATION_PCT": 50.0, "PANEL_B_SITUATION_PCT": 50.0,
            "PANEL_A_ANTENNA_PRESET": 0, "PANEL_B_ANTENNA_PRESET": 0,
            "PANEL_A_ANTENNA_BW": 360.0, "PANEL_B_ANTENNA_BW": 360.0,
            "PANEL_A_ANTENNA_AZ": 0.0, "PANEL_B_ANTENNA_AZ": 0.0,
            "PANEL_A_FRONT_BACK_DB": 25.0, "PANEL_B_FRONT_BACK_DB": 25.0,
            "PANEL_A_DOWNTILT_DEG": 0.0, "PANEL_B_DOWNTILT_DEG": 0.0,
            "PANEL_A_H_PATTERN": "", "PANEL_B_H_PATTERN": "",
            "PANEL_A_V_PATTERN": "", "PANEL_B_V_PATTERN": "",
            "PANEL_A_CLUTTER_MODEL": 0, "PANEL_B_CLUTTER_MODEL": 0,
            "PANEL_A_CLUTTER_RASTER": "", "PANEL_B_CLUTTER_RASTER": "",
            "PANEL_A_N0": 301.0, "PANEL_B_N0": 301.0,
            "PANEL_A_EPSILON": 15.0, "PANEL_B_EPSILON": 15.0,
            "PANEL_A_SIGMA": 0.005, "PANEL_B_SIGMA": 0.005,
            "OUTPUT_DIR": base, "DELTA_STYLE": 0, "DELTA_THRESHOLD_DB": 3.0,
        }
        result = alg.processAlgorithm(params, context, feedback)
        assert result is not None
