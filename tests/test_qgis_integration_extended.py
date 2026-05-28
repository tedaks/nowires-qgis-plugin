# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Docker QGIS integration tests for algorithm modules."""

import os

import numpy as np
import pytest

from qgis.core import QgsProcessingContext, QgsProcessingFeedback

pytestmark = pytest.mark.qgis_integration


class Feedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.messages = []

    def pushInfo(self, msg):
        self.messages.append(msg)

    def pushWarning(self, msg):
        self.messages.append(msg)


def _create_dem(path, south=0, north=5, west=0, east=5, nx=50, ny=50):
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


class TestRadioCoverageIntegration:
    def test_compute_itm_p2p_basic(self, qgis_app):
        from NoWires.radio_coverage.compute import compute_itm_p2p
        elevs = np.linspace(100, 95, 200)
        result = compute_itm_p2p(
            h_tx__meter=30.0, h_rx__meter=10.0,
            elevations=elevs, resolution=30.0,
            climate_idx=1, N_0=301.0, f__mhz=300.0,
            polarization=1, epsilon=15.0, sigma=0.005,
            time_pct=50, location_pct=50, situation_pct=50,
            eirp_dbm=30.0, ant_gain_adj=0.0, rx_gain_dbi=0.0,
            clutter_tx_db=0.0, clutter_rx_db=0.0, bel_rx_db=0.0,
        )
        assert result is not None
        assert "received_power_dbm" in result
        assert "total_path_loss_db" in result

    def test_coverage_report_empty_grid(self, qgis_app):
        import numpy as np
        from NoWires.radio_coverage.reporting import build_coverage_report_payload_for_grid
        from NoWires.radio_coverage.coverage_grids import CoverageGrids
        from NoWires.radio_coverage.analysis_params import CoverageAnalysisParams
        grid = np.full((5, 5), np.nan, dtype=np.float32)
        zeros = np.zeros((5, 5), dtype=np.float32)
        from unittest.mock import MagicMock
        mock_clutter = MagicMock()
        mock_clutter.tx_loss_db = 0.0
        payload = build_coverage_report_payload_for_grid(
            grids=CoverageGrids(
                prx_grid=grid, loss_grid=grid, itm_loss_grid=grid,
                clutter_loss_grid=zeros, clutter_rx_db_grid=zeros,
                bel_rx_db_grid=zeros,
                min_lat=0.0, max_lat=1.0, min_lon=0.0, max_lon=1.0),
            params=CoverageAnalysisParams(
                tx_lat=0.5, tx_lon=0.5, tx_h=30.0, rx_h=2.0,
                f_mhz=300.0, radius_km=5.0, grid_size=1,
                polarization=1, climate=1,
                tx_power=30.0, tx_gain=0.0, rx_gain=0.0,
                cable_loss=0.0, rx_sens=-100.0, clutter_enabled=False,
            ),
            clutter_source="none",
            tx_clutter_for_report=mock_clutter,
        )
        assert payload is not None

    def test_remove_coverage_legend_noop(self, qgis_app):
        from NoWires.radio_coverage.legend import remove_coverage_legend
        remove_coverage_legend()
        assert True

    def test_palette_apply_coverage_style(self, qgis_app, tmp_path):
        from NoWires.radio_coverage.palette import apply_coverage_style
        tif = str(tmp_path / "coverage.tif")
        _create_dem(tif)
        from qgis.core import QgsRasterLayer
        layer = QgsRasterLayer(tif, "Test Coverage")
        if layer.isValid():
            apply_coverage_style(layer)
            assert layer.renderer() is not None

    def test_opacity_dialog_smoke(self, qgis_app, tmp_path):
        from NoWires.radio_coverage.opacity import CoverageOpacityDialog
        tif = str(tmp_path / "opacity.tif")
        _create_dem(tif)
        from qgis.core import QgsRasterLayer
        layer = QgsRasterLayer(tif, "Opacity Test")
        if layer.isValid():
            dlg = CoverageOpacityDialog(layer, parent=None)
            assert dlg is not None
            dlg.deleteLater()


class TestThreeDIntegration:
    def test_highlight_nowires_layers(self, qgis_app, tmp_path):
        tif = str(tmp_path / "3d_test.tif")
        _create_dem(tif)
        from qgis.core import QgsRasterLayer, QgsProject
        layer = QgsRasterLayer(tif, "NoWires Coverage")
        QgsProject.instance().addMapLayer(layer)
        try:
            from NoWires.three_d import highlight_nowires_layers
            from unittest.mock import MagicMock
            mock_iface = MagicMock()
            mock_iface.mapCanvas.return_value = MagicMock()
            highlight_nowires_layers(mock_iface)
        finally:
            QgsProject.instance().removeMapLayer(layer)

    def test_configure_contours_for_3d(self, qgis_app, tmp_path):
        from qgis.core import QgsVectorLayer
        gpkg_path = str(tmp_path / "contour3d.gpkg")
        from osgeo import ogr, osr
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(gpkg_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        lyr = ds.CreateLayer("contours", srs, ogr.wkbLineString)
        lyr.CreateField(ogr.FieldDefn("ELEV", ogr.OFTReal))
        feat = ogr.Feature(lyr.GetLayerDefn())
        line = ogr.Geometry(ogr.wkbLineString)
        line.AddPoint(0, 0)
        line.AddPoint(1, 0)
        feat.SetGeometry(line)
        feat.SetField("ELEV", 100.0)
        lyr.CreateFeature(feat)
        ds = None

        layer = QgsVectorLayer(gpkg_path, "Contours")
        if layer.isValid():
            from NoWires.three_d import configure_contours_for_3d
            configure_contours_for_3d(layer)


class TestContourIntegration:
    def test_contour_smoothing_none(self, qgis_app, tmp_path):
        tif = str(tmp_path / "smooth_dem.tif")
        _create_dem(tif)
        from NoWires.contour.smoothing import smooth_contour_dem, SMOOTHING_NONE
        from NoWires.temp_manager import TempDirManager
        mgr = TempDirManager()
        tmp_dir = mgr.make_dir("smooth_test")
        try:
            smooth_contour_dem(
                SMOOTHING_NONE, tif, tmp_dir,
                Feedback(), 0.0, 1.0,
            )
        finally:
            mgr.cleanup()


class TestP2PIntegration:
    def test_p2p_link_param_class(self, qgis_app):
        from NoWires.p2p.analysis_params import P2PAnalysisParams
        params = P2PAnalysisParams(
            tx_lat=47.0, tx_lon=8.0, rx_lat=47.1, rx_lon=8.1,
            tx_h=30.0, rx_h=10.0, f_mhz=300.0,
            polarization=1, climate=1,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=30.0, tx_gain=0.0, rx_gain=0.0,
            cable_loss=0.0, rx_sens=-100.0, k_factor=1.333,
            n0=301.0, epsilon=15.0, sigma=0.005,
        )
        assert params.tx_lat == 47.0
        assert params.f_mhz == 300.0

    def test_p2p_outputs_write_fresnel_zone(self, qgis_app, tmp_path):
        from NoWires.p2p.outputs import write_fresnel_zone
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        poly_path = str(tmp_path / "fresnel_poly.gpkg")
        lines_path = str(tmp_path / "fresnel_lines.gpkg")
        distances = np.linspace(0, 5000, 50)
        terrain = np.full(50, 100.0)
        write_fresnel_zone(
            poly_path, lines_path, srs,
            0.0, 0.0, 0.05, 0.0,
            distances, terrain, terrain * 0.6, terrain * 0.3, 5000.0,
        )
        assert os.path.exists(poly_path)

    def test_p2p_symbology_applied(self, qgis_app, tmp_path):
        from qgis.core import QgsVectorLayer
        gpkg_path = str(tmp_path / "p2p_lines.gpkg")
        from osgeo import ogr, osr
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(gpkg_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        lyr = ds.CreateLayer("path", srs, ogr.wkbLineString)
        feat = ogr.Feature(lyr.GetLayerDefn())
        line = ogr.Geometry(ogr.wkbLineString)
        line.AddPoint(0, 0)
        line.AddPoint(1, 0)
        feat.SetGeometry(line)
        lyr.CreateFeature(feat)
        ds = None

        layer = QgsVectorLayer(gpkg_path, "P2P Path")
        if layer.isValid():
            from NoWires.p2p.symbology import apply_profile_line_symbology
            apply_profile_line_symbology(layer)


class TestProcessingUtilsIntegration:
    def test_queue_layer_loading(self, qgis_app, tmp_path):
        from NoWires.processing_utils import queue_layer_for_loading
        from qgis.core import QgsVectorLayer
        context = QgsProcessingContext()
        gpkg_path = str(tmp_path / "queue.gpkg")
        from osgeo import ogr, osr
        driver = ogr.GetDriverByName("GPKG")
        ds = driver.CreateDataSource(gpkg_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        lyr = ds.CreateLayer("test", srs, ogr.wkbPoint)
        feat = ogr.Feature(lyr.GetLayerDefn())
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint(0, 0)
        feat.SetGeometry(pt)
        lyr.CreateFeature(feat)
        ds = None

        layer = QgsVectorLayer(gpkg_path, "Test")
        queue_layer_for_loading(context, layer, "Test Layer")


class TestNowiresPluginIntegration:
    def test_provider_loads_all_algorithms(self, qgis_app):
        from NoWires.provider import NoWiresProvider
        provider = NoWiresProvider()
        provider.loadAlgorithms()
        names = [a.name() for a in provider.algorithms()]
        assert "p2p_analysis" in names
        assert "coverage_analysis" in names
        assert "coverage_comparison" in names
        assert "contour_lines" in names
        assert "batch_p2p_analysis" in names
        assert len(names) == 5
