# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""QGIS integration tests for algorithm execution and consistency.

Runs processAlgorithm() for P2P and Coverage using a synthetic DEM.
Requires QGIS_PREFIX_PATH to be set (QGIS Docker container).
"""

import os
import numpy as np
import pytest

try:
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsPointXY
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(
        not _HAS_QGIS,
        reason="QGIS integration tests require QGIS_PREFIX_PATH to be set",
    ),
    pytest.mark.qgis_integration,
]


def _create_synthetic_dem(path, south, north, west, east, nx=50, ny=50):
    from osgeo import gdal, osr
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, nx, ny, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetProjection(srs.ExportToWkt())
    dx = (east - west) / nx
    dy = (north - south) / ny
    ds.SetGeoTransform([west, dx, 0, north, 0, -dy])
    data = np.full((ny, nx), 100.0, dtype=np.float32)
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None
    return path


@pytest.fixture
def processing_context(qgis_app):
    return QgsProcessingContext()


@pytest.fixture
def feedback():
    return QgsProcessingFeedback()


class TestP2PAlgorithmExecution:
    def test_p2p_process_algorithm_runs_with_synthetic_dem(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.p2p import P2PAlgorithm
        from NoWires import dem_downloader as dd_mod
        from NoWires import clutter as clutter_mod

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(
            dem_path, south=13.9, north=14.1,
            west=120.9, east=121.1, nx=20, ny=20,
        )

        monkeypatch.setattr(dd_mod, "ensure_dem_for_area", lambda *a, **kw: dem_path)
        monkeypatch.setattr(clutter_mod, "ensure_clutter_grid_for_area", lambda *a, **kw: None)

        alg = P2PAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.TX_POINT: QgsPointXY(121.0, 14.0),
            alg.RX_POINT: QgsPointXY(121.01, 14.0),
            alg.TX_HEIGHT: 30.0,
            alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0,
            alg.POLARIZATION: 1,
            alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0,
            alg.LOCATION_PCT: 50.0,
            alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 30.0,
            alg.TX_GAIN: 10.0,
            alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 1.0,
            alg.RX_SENSITIVITY: -90.0,
            alg.K_FACTOR_PRESET: 2,
            alg.K_FACTOR: 1.333,
            alg.N0: 301.0,
            alg.EPSILON: 15.0,
            alg.SIGMA: 0.005,
            alg.TX_ANTENNA_PRESET: 0,
            alg.TX_ANTENNA_AZ: 0.0,
            alg.TX_FRONT_BACK_DB: 25.0,
            alg.TX_DOWNTILT_DEG: 0.0,
            alg.TX_H_PATTERN: "",
            alg.TX_V_PATTERN: "",
            alg.RX_ANTENNA_PRESET: 0,
            alg.RX_ANTENNA_AZ: 0.0,
            alg.RX_FRONT_BACK_DB: 25.0,
            alg.RX_DOWNTILT_DEG: 0.0,
            alg.RX_H_PATTERN: "",
            alg.RX_V_PATTERN: "",
            alg.CLUTTER_MODEL: 0,
            alg.CCH_OVERRIDE: 0.0,
            alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0,
            alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0,
            alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False,
            alg.BEL_BUILDING_TYPE: 0,
            alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.SHOW_CHART: False,
            alg.OUTPUT_PROFILE: str(tmp_path / "profile.gpkg"),
            alg.OUTPUT_FRESNEL: str(tmp_path / "fresnel.gpkg"),
            alg.OUTPUT_MARKERS: str(tmp_path / "markers.gpkg"),
            alg.OUTPUT_REPORT_CSV: str(tmp_path / "report.csv"),
            alg.OUTPUT_REPORT_JSON: str(tmp_path / "report.json"),
            alg.OUTPUT_REPORT_HTML: str(tmp_path / "report.html"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)
        assert results[alg.OUTPUT_PROFILE] is not None
        assert os.path.exists(results[alg.OUTPUT_PROFILE])


class TestCoverageAlgorithmExecution:
    def test_coverage_process_algorithm_runs_with_synthetic_dem(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.coverage import CoverageAlgorithm
        from NoWires import dem_downloader as dd_mod

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(
            dem_path, south=13.9, north=14.1,
            west=120.9, east=121.1, nx=30, ny=30,
        )

        monkeypatch.setattr(dd_mod, "ensure_dem_for_area", lambda *a, **kw: dem_path)

        alg = CoverageAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.TX_POINT: QgsPointXY(121.0, 14.0),
            alg.TX_HEIGHT: 30.0,
            alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0,
            alg.POLARIZATION: 1,
            alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0,
            alg.LOCATION_PCT: 50.0,
            alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 30.0,
            alg.TX_GAIN: 10.0,
            alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 1.0,
            alg.RX_SENSITIVITY: -90.0,
            alg.N0: 301.0,
            alg.EPSILON: 15.0,
            alg.SIGMA: 0.005,
            alg.RADIUS_KM: 0.5,
            alg.GRID_SIZE: 0,
            alg.ANTENNA_PRESET: 0,
            alg.ANTENNA_AZ: 0.0,
            alg.ANTENNA_BW: 360.0,
            alg.FRONT_BACK_DB: 25.0,
            alg.DOWNTILT_DEG: 0.0,
            alg.H_PATTERN: "",
            alg.V_PATTERN: "",
            alg.CLUTTER_MODEL: 0,
            alg.CCH_OVERRIDE: 0.0,
            alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0,
            alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0,
            alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False,
            alg.BEL_BUILDING_TYPE: 0,
            alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.OUTPUT_RASTER: str(tmp_path / "coverage.tif"),
            alg.OUTPUT_REPORT_CSV: str(tmp_path / "report.csv"),
            alg.OUTPUT_REPORT_JSON: str(tmp_path / "report.json"),
            alg.OUTPUT_REPORT_HTML: str(tmp_path / "report.html"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)
        assert results[alg.OUTPUT_RASTER] is not None
        assert os.path.exists(results[alg.OUTPUT_RASTER])

        from osgeo import gdal
        ds = gdal.Open(results[alg.OUTPUT_RASTER])
        assert ds is not None
        ds = None


class TestAlgorithmParameterConsistency:
    def test_p2p_algorithm_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.p2p import P2PAlgorithm
        alg = P2PAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "p2p_analysis"
        assert alg.TX_POINT is not None
        assert alg.OUTPUT_PROFILE is not None

    def test_coverage_algorithm_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.coverage import CoverageAlgorithm
        alg = CoverageAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "coverage_analysis"
        assert alg.TX_POINT is not None
        assert alg.RADIUS_KM is not None
        assert alg.OUTPUT_RASTER is not None

    def test_batch_algorithm_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm
        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "batch_p2p_analysis"

    def test_contour_algorithm_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.contour import ContourLinesAlgorithm
        alg = ContourLinesAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "contour_lines"
        assert alg.OUTPUT is not None

    def test_comparison_algorithm_has_all_required_params(self, qgis_app):
        from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm
        alg = CoverageComparisonAlgorithm()
        alg.initAlgorithm({})
        assert alg.name() == "coverage_comparison"
        assert alg.OUTPUT_DELTA is not None


class TestBatchAlgorithmExecution:
    def test_batch_one_to_many_process_algorithm_runs(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm
        from NoWires import dem_downloader as dd_mod
        from osgeo import ogr, osr

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(
            dem_path, south=13.9, north=14.1,
            west=120.9, east=121.1, nx=20, ny=20,
        )

        monkeypatch.setattr(dd_mod, "ensure_dem_for_area", lambda *a, **kw: dem_path)

        rx_path = str(tmp_path / "rx_points.gpkg")
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(rx_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        layer = ds.CreateLayer("rx", srs=srs, geom_type=ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("height", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("gain_db", ogr.OFTReal))
        for lon, lat in [(121.005, 14.0), (121.01, 14.0)]:
            feat = ogr.Feature(layer.GetLayerDefn())
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.AddPoint(lon, lat)
            feat.SetGeometry(geom)
            feat.SetField("height", 10.0)
            feat.SetField("gain_db", 8.0)
            layer.CreateFeature(feat)
        ds = None

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 0,
            alg.TX_POINT: QgsPointXY(121.0, 14.0),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0, alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 30.0, alg.TX_GAIN: 10.0, alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 1.0, alg.RX_SENSITIVITY: -90.0,
            alg.K_FACTOR_PRESET: 2, alg.K_FACTOR: 1.333,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
            alg.RX_LAYER: rx_path,
            alg.TX_ANTENNA_PRESET: 0, alg.TX_ANTENNA_AZ: 0.0, alg.TX_FRONT_BACK_DB: 25.0,
            alg.RX_ANTENNA_PRESET: 0, alg.RX_ANTENNA_AZ: 0.0, alg.RX_FRONT_BACK_DB: 25.0,
            alg.CLUTTER_MODEL: 0, alg.CCH_OVERRIDE: 0.0, alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0, alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0, alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False, alg.BEL_BUILDING_TYPE: 0, alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.RANK_BY: 0,
            alg.OUTPUT_MARKERS: str(tmp_path / "markers.gpkg"),
            alg.OUTPUT_CSV: str(tmp_path / "results.csv"),
            alg.OUTPUT_JSON: str(tmp_path / "results.json"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)
        assert results[alg.OUTPUT_MARKERS] is not None
        assert os.path.exists(results[alg.OUTPUT_MARKERS])


class TestContourAlgorithmExecution:
    def test_contour_validate_aoi_with_valid_rectangle(self, qgis_app):
        from NoWires.algorithm.contour import ContourLinesAlgorithm
        from qgis.core import QgsRectangle, QgsProcessingContext

        alg = ContourLinesAlgorithm()
        alg.initAlgorithm({})

        rect = QgsRectangle(120.9, 13.9, 121.1, 14.1)
        aoi, geom = alg._validate_aoi(
            {alg.AREA_OF_INTEREST: rect},
            QgsProcessingContext(),
        )
        assert aoi.width() < 5.0
        assert aoi.height() < 5.0
        assert not geom.isEmpty()

    def test_contour_validate_aoi_rejects_large_area(self, qgis_app):
        from NoWires.algorithm.contour import ContourLinesAlgorithm
        from qgis.core import QgsRectangle, QgsProcessingContext
        from qgis.core import QgsProcessingException

        alg = ContourLinesAlgorithm()
        alg.initAlgorithm({})

        rect = QgsRectangle(-10, -10, 10, 10)
        with pytest.raises(QgsProcessingException, match="too large"):
            alg._validate_aoi({alg.AREA_OF_INTEREST: rect}, QgsProcessingContext())


