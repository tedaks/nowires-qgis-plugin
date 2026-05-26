# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Batch P2P and Coverage Analysis integration tests with Philippines coordinates inside QGIS 4."""

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
    pytest.mark.slow,
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


def _write_point_gpkg(path, points, crs_epsg=4326):
    from osgeo import ogr, osr
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(crs_epsg)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("points", srs=srs, geom_type=ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("height", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("gain_db", ogr.OFTReal))
    for pt in points:
        feat = ogr.Feature(layer.GetLayerDefn())
        geom = ogr.Geometry(ogr.wkbPoint)
        geom.AddPoint(pt["lon"], pt["lat"])
        feat.SetGeometry(geom)
        feat.SetField("height", pt.get("height", 10.0))
        feat.SetField("gain_db", pt.get("gain_db", 2.0))
        layer.CreateFeature(feat)
    ds = None
    return path


def _patch_dem_download(monkeypatch, dem_path):
    """Patch ensure_dem_for_area in algorithm modules that have already
    imported it via ``from NoWires.dem_downloader import ensure_dem_for_area``.

    Patching only ``NoWires.dem_downloader.ensure_dem_for_area`` is
    insufficient because the algorithm modules captured the function
    reference at import time.
    """
    import NoWires.algorithm.batch as _batch
    import NoWires.algorithm.coverage as _coverage
    monkeypatch.setattr(_batch, "ensure_dem_for_area", lambda *a, **kw: dem_path)
    monkeypatch.setattr(_coverage, "ensure_dem_for_area", lambda *a, **kw: dem_path)


@pytest.fixture
def processing_context(qgis_app):
    return QgsProcessingContext()


@pytest.fixture
def feedback():
    return QgsProcessingFeedback()


class TestBatchP2PPhilippines:
    """Batch P2P analysis with real-world Philippines coordinates.

    TX site at Manila, RX points across Metro Manila and nearby Luzon cities.
    Uses a synthetic flat DEM for deterministic, offline testing.
    """

    TX_MANILA = {"lat": 14.5995, "lon": 120.9842, "label": "Manila TX"}

    RX_METRO_MANILA = [
        {"lat": 14.6516, "lon": 121.0492, "label": "Quezon City"},
        {"lat": 14.5547, "lon": 121.0244, "label": "Makati"},
        {"lat": 14.6645, "lon": 120.9718, "label": "Caloocan"},
        {"lat": 14.5764, "lon": 121.0851, "label": "Pasig"},
        {"lat": 14.5115, "lon": 121.0043, "label": "Paranaque"},
        {"lat": 14.6019, "lon": 121.0984, "label": "Marikina"},
        {"lat": 14.4805, "lon": 120.9819, "label": "Las Pinas"},
        {"lat": 14.7050, "lon": 121.0111, "label": "Valenzuela"},
    ]

    DEM_SOUTH = 14.35
    DEM_NORTH = 14.85
    DEM_WEST = 120.80
    DEM_EAST = 121.25

    def test_batch_one_to_many_manila_to_metro_manila(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path, south=self.DEM_SOUTH, north=self.DEM_NORTH,
                             west=self.DEM_WEST, east=self.DEM_EAST, nx=40, ny=40)
        _patch_dem_download(monkeypatch, dem_path)

        rx_path = str(tmp_path / "rx_points.gpkg")
        _write_point_gpkg(rx_path, self.RX_METRO_MANILA)

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 0,
            alg.TX_POINT: QgsPointXY(self.TX_MANILA["lon"], self.TX_MANILA["lat"]),
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
        assert results[alg.OUTPUT_CSV] is not None
        assert os.path.exists(results[alg.OUTPUT_CSV])
        assert results[alg.OUTPUT_JSON] is not None
        assert os.path.exists(results[alg.OUTPUT_JSON])

        import json
        with open(results[alg.OUTPUT_JSON]) as fh:
            batch_data = json.load(fh)
        assert isinstance(batch_data, dict)
        assert batch_data["report_type"] == "batch_p2p"
        assert batch_data["total_links"] == len(self.RX_METRO_MANILA)
        assert batch_data["viable_links"] >= 0
        assert isinstance(batch_data["results"], list)
        assert len(batch_data["results"]) == len(self.RX_METRO_MANILA)

        for entry in batch_data["results"]:
            assert "margin_db" in entry
            assert "status" in entry
            assert "distance_km" in entry
            assert "itm_loss_db" in entry

        assert os.path.getsize(results[alg.OUTPUT_CSV]) > 0

    def test_batch_many_to_one_luzon_cities_to_manila(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path, south=self.DEM_SOUTH, north=self.DEM_NORTH,
                             west=self.DEM_WEST, east=self.DEM_EAST, nx=40, ny=40)
        _patch_dem_download(monkeypatch, dem_path)

        tx_path = str(tmp_path / "tx_points.gpkg")
        _write_point_gpkg(tx_path, self.RX_METRO_MANILA)

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 1,
            alg.TX_LAYER: tx_path,
            alg.RX_POINT: QgsPointXY(self.TX_MANILA["lon"], self.TX_MANILA["lat"]),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0, alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 30.0, alg.TX_GAIN: 10.0, alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 1.0, alg.RX_SENSITIVITY: -90.0,
            alg.K_FACTOR_PRESET: 2, alg.K_FACTOR: 1.333,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
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
        assert results[alg.OUTPUT_CSV] is not None
        assert os.path.exists(results[alg.OUTPUT_CSV])
        assert results[alg.OUTPUT_JSON] is not None
        assert os.path.exists(results[alg.OUTPUT_JSON])

        import json
        with open(results[alg.OUTPUT_JSON]) as fh:
            batch_data = json.load(fh)
        assert isinstance(batch_data, dict)
        assert batch_data["total_links"] == len(self.RX_METRO_MANILA)
        assert len(batch_data["results"]) == len(self.RX_METRO_MANILA)

    def test_batch_one_to_many_link_viability(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        """Verify all links are VIABLE for short-range metro-area links."""
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path, south=self.DEM_SOUTH, north=self.DEM_NORTH,
                             west=self.DEM_WEST, east=self.DEM_EAST, nx=40, ny=40)
        _patch_dem_download(monkeypatch, dem_path)

        rx_path = str(tmp_path / "rx_points.gpkg")
        _write_point_gpkg(rx_path, self.RX_METRO_MANILA)

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 0,
            alg.TX_POINT: QgsPointXY(self.TX_MANILA["lon"], self.TX_MANILA["lat"]),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0, alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 43.0, alg.TX_GAIN: 10.0, alg.RX_GAIN: 2.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -100.0,
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

        import json
        with open(results[alg.OUTPUT_JSON]) as fh:
            batch_data = json.load(fh)

        assert batch_data["total_links"] == len(self.RX_METRO_MANILA)
        assert len(batch_data["results"]) > 0
        for entry in batch_data["results"]:
            assert entry["status"] == "VIABLE"
            assert entry["margin_db"] > 0


class TestBatchP2PPhilippinesCrossIsland:
    """Batch P2P spanning multiple Philippine islands.

    Manila TX to Cebu, Davao, Puerto Princesa, Baguio, Iligan, and Iriga.
    Uses a wide synthetic DEM covering the full archipelago extent.
    """

    TX_MANILA = {"lat": 14.5995, "lon": 120.9842, "label": "Manila TX"}

    RX_CROSS_ISLAND = [
        {"lat": 10.3157, "lon": 123.8854, "label": "Cebu City"},
        {"lat": 7.0700, "lon": 125.6100, "label": "Davao City"},
        {"lat": 9.7350, "lon": 118.7400, "label": "Puerto Princesa"},
        {"lat": 16.4023, "lon": 120.5960, "label": "Baguio City"},
        {"lat": 8.2280, "lon": 124.2450, "label": "Iligan City"},
        {"lat": 13.4040, "lon": 123.3760, "label": "Iriga City"},
    ]

    DEM_SOUTH = 5.0
    DEM_NORTH = 18.0
    DEM_WEST = 116.0
    DEM_EAST = 128.0

    def test_batch_one_to_many_manila_to_cross_island(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path, south=self.DEM_SOUTH, north=self.DEM_NORTH,
                             west=self.DEM_WEST, east=self.DEM_EAST, nx=60, ny=60)
        _patch_dem_download(monkeypatch, dem_path)

        rx_path = str(tmp_path / "rx_points.gpkg")
        _write_point_gpkg(rx_path, self.RX_CROSS_ISLAND)

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 0,
            alg.TX_POINT: QgsPointXY(self.TX_MANILA["lon"], self.TX_MANILA["lat"]),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 700.0, alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 46.0, alg.TX_GAIN: 12.0, alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -110.0,
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
        assert results[alg.OUTPUT_CSV] is not None
        assert results[alg.OUTPUT_JSON] is not None

        import json
        with open(results[alg.OUTPUT_JSON]) as fh:
            batch_data = json.load(fh)
        assert isinstance(batch_data, dict)
        assert batch_data["total_links"] == len(self.RX_CROSS_ISLAND)
        assert len(batch_data["results"]) == len(self.RX_CROSS_ISLAND)

        for entry in batch_data["results"]:
            assert "margin_db" in entry
            assert "status" in entry
            assert "distance_km" in entry
            assert "itm_loss_db" in entry

    def test_batch_cross_island_distance_monotonic(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        """ITM loss should increase with distance on a flat synthetic DEM.

        Ranked by path loss ascending: first entry should be the closest RX,
        last entry the farthest RX.
        """
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path, south=self.DEM_SOUTH, north=self.DEM_NORTH,
                             west=self.DEM_WEST, east=self.DEM_EAST, nx=60, ny=60)
        _patch_dem_download(monkeypatch, dem_path)

        rx_path = str(tmp_path / "rx_points.gpkg")
        _write_point_gpkg(rx_path, self.RX_CROSS_ISLAND)

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 0,
            alg.TX_POINT: QgsPointXY(self.TX_MANILA["lon"], self.TX_MANILA["lat"]),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 700.0, alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 46.0, alg.TX_GAIN: 12.0, alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -110.0,
            alg.K_FACTOR_PRESET: 2, alg.K_FACTOR: 1.333,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
            alg.RX_LAYER: rx_path,
            alg.RANK_BY: 1,
            alg.OUTPUT_MARKERS: str(tmp_path / "markers.gpkg"),
            alg.OUTPUT_CSV: str(tmp_path / "results.csv"),
            alg.OUTPUT_JSON: str(tmp_path / "results.json"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)

        import json
        with open(results[alg.OUTPUT_JSON]) as fh:
            batch_data = json.load(fh)

        entries = batch_data["results"]
        assert len(entries) >= 2
        for i in range(len(entries) - 1):
            assert entries[i]["distance_km"] <= entries[i + 1]["distance_km"]
            assert entries[i]["itm_loss_db"] <= entries[i + 1]["itm_loss_db"]

    def test_batch_cross_island_sort_by_margin(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        """Rank by margin: first entry should have highest margin (closest)."""
        from NoWires.algorithm.batch import BatchAnalysisAlgorithm

        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path, south=self.DEM_SOUTH, north=self.DEM_NORTH,
                             west=self.DEM_WEST, east=self.DEM_EAST, nx=60, ny=60)
        _patch_dem_download(monkeypatch, dem_path)

        rx_path = str(tmp_path / "rx_points.gpkg")
        _write_point_gpkg(rx_path, self.RX_CROSS_ISLAND)

        alg = BatchAnalysisAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.MODE: 0,
            alg.TX_POINT: QgsPointXY(self.TX_MANILA["lon"], self.TX_MANILA["lat"]),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 700.0, alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 46.0, alg.TX_GAIN: 12.0, alg.RX_GAIN: 8.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -110.0,
            alg.K_FACTOR_PRESET: 2, alg.K_FACTOR: 1.333,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
            alg.RX_LAYER: rx_path,
            alg.RANK_BY: 0,
            alg.OUTPUT_MARKERS: str(tmp_path / "markers.gpkg"),
            alg.OUTPUT_CSV: str(tmp_path / "results.csv"),
            alg.OUTPUT_JSON: str(tmp_path / "results.json"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)

        import json
        with open(results[alg.OUTPUT_JSON]) as fh:
            batch_data = json.load(fh)

        entries = batch_data["results"]
        assert len(entries) >= 2
        for i in range(len(entries) - 1):
            assert entries[i]["margin_db"] >= entries[i + 1]["margin_db"]


class TestCoveragePhilippines:
    """Coverage Analysis with Philippines-located transmitters.

    Tests coverage heatmap raster generation for Manila and Cebu sites
    using synthetic flat DEM for deterministic, offline validation.
    """

    TX_MANILA = (120.9842, 14.5995)
    TX_CEBU = (123.8854, 10.3157)

    def test_coverage_manila_50km(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.coverage import CoverageAlgorithm

        radius_km = 50.0
        pad = 0.8
        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path,
            south=self.TX_MANILA[1] - pad, north=self.TX_MANILA[1] + pad,
            west=self.TX_MANILA[0] - pad, east=self.TX_MANILA[0] + pad,
            nx=64, ny=64)
        _patch_dem_download(monkeypatch, dem_path)

        alg = CoverageAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.TX_POINT: QgsPointXY(*self.TX_MANILA),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0, alg.RADIUS_KM: radius_km, alg.GRID_SIZE: 0,
            alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 43.0, alg.TX_GAIN: 10.0, alg.RX_GAIN: 2.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -100.0,
            alg.ANTENNA_PRESET: 0, alg.ANTENNA_AZ: 0.0, alg.ANTENNA_BW: 360.0,
            alg.FRONT_BACK_DB: 25.0, alg.DOWNTILT_DEG: 0.0,
            alg.H_PATTERN: "", alg.V_PATTERN: "",
            alg.CLUTTER_MODEL: 0, alg.CCH_OVERRIDE: 0.0, alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0, alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0, alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False, alg.BEL_BUILDING_TYPE: 0, alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
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
        assert ds.RasterXSize > 0
        assert ds.RasterYSize > 0
        band = ds.GetRasterBand(1)
        data = band.ReadAsArray()
        assert data is not None
        valid_mask = data > -9000
        assert np.any(valid_mask), "Coverage raster has no valid pixels"
        ds = None

    def test_coverage_cebu_30km(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.coverage import CoverageAlgorithm

        radius_km = 30.0
        pad = 0.6
        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path,
            south=self.TX_CEBU[1] - pad, north=self.TX_CEBU[1] + pad,
            west=self.TX_CEBU[0] - pad, east=self.TX_CEBU[0] + pad,
            nx=64, ny=64)
        _patch_dem_download(monkeypatch, dem_path)

        alg = CoverageAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.TX_POINT: QgsPointXY(*self.TX_CEBU),
            alg.TX_HEIGHT: 20.0, alg.RX_HEIGHT: 5.0,
            alg.FREQ_MHZ: 1800.0, alg.RADIUS_KM: radius_km, alg.GRID_SIZE: 0,
            alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 40.0, alg.TX_GAIN: 8.0, alg.RX_GAIN: 2.0,
            alg.CABLE_LOSS: 1.0, alg.RX_SENSITIVITY: -95.0,
            alg.ANTENNA_PRESET: 0, alg.ANTENNA_AZ: 0.0, alg.ANTENNA_BW: 360.0,
            alg.FRONT_BACK_DB: 25.0, alg.DOWNTILT_DEG: 0.0,
            alg.H_PATTERN: "", alg.V_PATTERN: "",
            alg.CLUTTER_MODEL: 0, alg.CCH_OVERRIDE: 0.0, alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0, alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0, alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False, alg.BEL_BUILDING_TYPE: 0, alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
            alg.OUTPUT_RASTER: str(tmp_path / "coverage.tif"),
            alg.OUTPUT_REPORT_CSV: str(tmp_path / "report.csv"),
            alg.OUTPUT_REPORT_JSON: str(tmp_path / "report.json"),
            alg.OUTPUT_REPORT_HTML: str(tmp_path / "report.html"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)

        assert results[alg.OUTPUT_RASTER] is not None
        assert os.path.exists(results[alg.OUTPUT_RASTER])
        assert results[alg.OUTPUT_REPORT_JSON] is not None

        from osgeo import gdal
        ds = gdal.Open(results[alg.OUTPUT_RASTER])
        assert ds is not None
        ds = None

    def test_coverage_manila_report_has_expected_keys(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        from NoWires.algorithm.coverage import CoverageAlgorithm

        radius_km = 10.0
        pad = 0.3
        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path,
            south=self.TX_MANILA[1] - pad, north=self.TX_MANILA[1] + pad,
            west=self.TX_MANILA[0] - pad, east=self.TX_MANILA[0] + pad,
            nx=32, ny=32)
        _patch_dem_download(monkeypatch, dem_path)

        alg = CoverageAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.TX_POINT: QgsPointXY(*self.TX_MANILA),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0, alg.RADIUS_KM: radius_km, alg.GRID_SIZE: 0,
            alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 43.0, alg.TX_GAIN: 10.0, alg.RX_GAIN: 2.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -100.0,
            alg.ANTENNA_PRESET: 0, alg.ANTENNA_AZ: 0.0, alg.ANTENNA_BW: 360.0,
            alg.FRONT_BACK_DB: 25.0, alg.DOWNTILT_DEG: 0.0,
            alg.H_PATTERN: "", alg.V_PATTERN: "",
            alg.CLUTTER_MODEL: 0, alg.CCH_OVERRIDE: 0.0, alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0, alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0, alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False, alg.BEL_BUILDING_TYPE: 0, alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
            alg.OUTPUT_RASTER: str(tmp_path / "coverage.tif"),
            alg.OUTPUT_REPORT_JSON: str(tmp_path / "report.json"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)

        import json
        with open(results[alg.OUTPUT_REPORT_JSON]) as fh:
            report = json.load(fh)
        assert report["report_type"] == "coverage"
        assert report["generated_by"] == "NoWires"
        assert "inputs" in report
        assert "results" in report
        inp = report["inputs"]
        assert inp["tx_lat"] == pytest.approx(self.TX_MANILA[1], abs=1e-4)
        assert "tx_lon" in inp

    def test_coverage_manila_sector_120deg_beam(
        self, qgis_app, processing_context, feedback, monkeypatch, tmp_path,
    ):
        """Coverage with a 120-degree sector antenna at Manila TX."""
        from NoWires.algorithm.coverage import CoverageAlgorithm

        radius_km = 20.0
        pad = 0.4
        dem_path = str(tmp_path / "dem.tif")
        _create_synthetic_dem(dem_path,
            south=self.TX_MANILA[1] - pad, north=self.TX_MANILA[1] + pad,
            west=self.TX_MANILA[0] - pad, east=self.TX_MANILA[0] + pad,
            nx=48, ny=48)
        _patch_dem_download(monkeypatch, dem_path)

        alg = CoverageAlgorithm()
        alg.initAlgorithm({})

        params = {
            alg.TX_POINT: QgsPointXY(*self.TX_MANILA),
            alg.TX_HEIGHT: 30.0, alg.RX_HEIGHT: 10.0,
            alg.FREQ_MHZ: 900.0, alg.RADIUS_KM: radius_km, alg.GRID_SIZE: 0,
            alg.POLARIZATION: 1, alg.CLIMATE: 1,
            alg.TIME_PCT: 50.0, alg.LOCATION_PCT: 50.0, alg.SITUATION_PCT: 50.0,
            alg.TX_POWER: 43.0, alg.TX_GAIN: 10.0, alg.RX_GAIN: 2.0,
            alg.CABLE_LOSS: 2.0, alg.RX_SENSITIVITY: -100.0,
            alg.ANTENNA_PRESET: 0, alg.ANTENNA_AZ: 135.0, alg.ANTENNA_BW: 120.0,
            alg.FRONT_BACK_DB: 25.0, alg.DOWNTILT_DEG: 0.0,
            alg.H_PATTERN: "", alg.V_PATTERN: "",
            alg.CLUTTER_MODEL: 0, alg.CCH_OVERRIDE: 0.0, alg.CLUTTER_RASTER: "",
            alg.TX_CLUTTER_OVERRIDE: 0, alg.RX_CLUTTER_OVERRIDE: 0,
            alg.CLUTTER_PERCENTILE: 50.0, alg.STREET_WIDTH: 27.0,
            alg.BEL_ENABLED: False, alg.BEL_BUILDING_TYPE: 0, alg.BEL_ELEVATION_ANGLE: 0.0,
            alg.N0: 301.0, alg.EPSILON: 15.0, alg.SIGMA: 0.005,
            alg.OUTPUT_RASTER: str(tmp_path / "coverage.tif"),
            alg.OUTPUT_REPORT_JSON: str(tmp_path / "report.json"),
        }

        results = alg.processAlgorithm(params, processing_context, feedback)

        assert results[alg.OUTPUT_RASTER] is not None
        assert os.path.exists(results[alg.OUTPUT_RASTER])

        from osgeo import gdal
        ds = gdal.Open(results[alg.OUTPUT_RASTER])
        assert ds is not None
        band = ds.GetRasterBand(1)
        data = band.ReadAsArray()
        assert data is not None
        valid_mask = data > -9000
        assert np.any(valid_mask)
        ds = None
