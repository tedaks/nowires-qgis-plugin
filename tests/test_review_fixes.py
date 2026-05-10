# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for issues found during full code review."""

import os
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest

# Ensure the coverage_analysis_params module can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from coverage_analysis_params import CoverageAnalysisParams


def _install_qgis_stubs():
    qgis = types.ModuleType("qgis")
    core = types.ModuleType("qgis.core")
    pyqt = types.ModuleType("qgis.PyQt")
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtgui = types.ModuleType("qgis.PyQt.QtGui")
    qtwidgets = types.ModuleType("qgis.PyQt.QtWidgets")

    class QgsProcessingException(Exception):
        pass

    class QgsProcessingAlgorithm:
        def flags(self):
            return 0

    class QCoreApplication:
        @staticmethod
        def translate(_context, string):
            return string

    class QEvent:
        class Type:
            Resize = 0
            Show = 1

    class Qt:
        class WidgetAttribute:
            WA_TransparentForMouseEvents = 0

        class CheckState:
            Checked = 1

    class Qgis:
        class ProcessingAlgorithmFlag:
            NoThreading = 1

        class GeometryType:
            Point = 0

        class RasterElevationMode:
            RepresentsElevationSurface = 0

    class Project:
        def writeEntry(self, *_args):
            return True

        def layerTreeRoot(self):
            return MagicMock()

    class QgsProject:
        @staticmethod
        def instance():
            return Project()

    class QgsProcessingContext:
        class LayerDetails:
            def __init__(self, *args):
                self.args = args

    class QgsRasterLayer:
        def __init__(self, *_args):
            pass

        def isValid(self):
            return False

    class QPainter:
        class CompositionMode:
            CompositionMode_ColorDodge = 0

    core.QgsProcessingException = QgsProcessingException
    core.QgsProcessingAlgorithm = QgsProcessingAlgorithm
    core.QCoreApplication = QCoreApplication
    core.Qgis = Qgis
    core.QgsProject = QgsProject
    core.QgsProcessingContext = QgsProcessingContext
    core.QgsRasterLayer = QgsRasterLayer
    core.QgsApplication = MagicMock()
    core.QgsAuthMethodConfig = MagicMock()
    core.__getattr__ = lambda _name: MagicMock()
    qtcore.QCoreApplication = QCoreApplication
    qtcore.QEvent = QEvent
    qtcore.Qt = Qt
    qtcore.__getattr__ = lambda _name: MagicMock()
    qtgui.QPainter = QPainter
    qtgui.__getattr__ = lambda _name: MagicMock()
    qtwidgets.__getattr__ = lambda _name: MagicMock()

    sys.modules["qgis"] = qgis
    sys.modules["qgis.core"] = core
    sys.modules["qgis.PyQt"] = pyqt
    sys.modules["qgis.PyQt.QtCore"] = qtcore
    sys.modules["qgis.PyQt.QtGui"] = qtgui
    sys.modules["qgis.PyQt.QtWidgets"] = qtwidgets


_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))

# Don't poison sys.modules["qgis.core"] when a real QGIS runtime is present;
# its `__getattr__ = lambda _name: MagicMock()` would make integration tests
# elsewhere see MagicMocks for QGIS classes (e.g. QgsProcessingProvider),
# breaking provider instantiation in collection-shared state.
if not _HAS_REAL_QGIS:
    _install_qgis_stubs()

pytestmark = pytest.mark.skipif(
    _HAS_REAL_QGIS,
    reason="Mock-based regression tests must not run against real QGIS extensions",
)


@pytest.fixture(autouse=True)
def qgis_stubs():
    _install_qgis_stubs()


class Feedback:
    def __init__(self):
        self.messages = []
        self.progress = []

    def pushInfo(self, message):
        self.messages.append(message)

    def pushWarning(self, message):
        self.messages.append(message)

    def setProgress(self, value):
        self.progress.append(value)

    def isCanceled(self):
        return False


def test_feat_attr_returns_default_when_field_is_missing():
    from NoWires.batch_outputs import _feat_attr

    class FeatureWithoutField:
        def attribute(self, name):
            raise KeyError(name)

    feature = FeatureWithoutField()

    assert _feat_attr(feature, "height", 10.0) == 10.0
    assert _feat_attr(feature, "antenna_preset", None) is None


def test_short_longitude_bounds_cross_antimeridian_without_global_extent():
    from NoWires.geo_bounds import shortest_longitude_bounds

    west, east = shortest_longitude_bounds(179.5, -179.5, 0.25)

    assert west > east
    assert west == 179.25
    assert east == -179.25


def test_tile_clip_geometry_splits_antimeridian_bounds():
    from NoWires.tile_download_base import _aoi_geometry_for_bounds

    calls = []

    class Ring:
        def __init__(self):
            self.points = []

        def AddPoint(self, lon, lat):
            self.points.append((lon, lat))

    class Polygon:
        def __init__(self):
            self.rings = []

        def AddGeometry(self, ring):
            self.rings.append(ring)

    class MultiPolygon:
        def __init__(self):
            self.polygons = []

        def AddGeometry(self, polygon):
            self.polygons.append(polygon)

    class Ogr:
        wkbLinearRing = "ring"
        wkbPolygon = "polygon"
        wkbMultiPolygon = "multipolygon"

        def Geometry(self, geom_type):
            calls.append(geom_type)
            if geom_type == self.wkbLinearRing:
                return Ring()
            if geom_type == self.wkbPolygon:
                return Polygon()
            if geom_type == self.wkbMultiPolygon:
                return MultiPolygon()
            raise AssertionError(geom_type)

    geom = _aoi_geometry_for_bounds(10.0, 11.0, 179.5, -179.5, Ogr())

    assert calls[0] == "multipolygon"
    assert len(geom.polygons) == 2
    assert geom.polygons[0].rings[0].points == [
        (179.5, 10.0),
        (180.0, 10.0),
        (180.0, 11.0),
        (179.5, 11.0),
        (179.5, 10.0),
    ]
    assert geom.polygons[1].rings[0].points == [
        (-180.0, 10.0),
        (-179.5, 10.0),
        (-179.5, 11.0),
        (-180.0, 11.0),
        (-180.0, 10.0),
    ]


def test_coverage_reports_are_written_even_when_raster_layer_is_invalid(monkeypatch, tmp_path):
    import NoWires.algorithm_coverage as module

    class InvalidRasterLayer:
        def __init__(self, path, name):
            self.path = path
            self.name_value = name

        def isValid(self):
            return False

        def error(self):
            class _Err:
                def summary(self):
                    return "mock error"
            return _Err()

    class Algorithm(module.CoverageAlgorithm):
        def parameterAsFileOutput(self, parameters, name, context):
            return parameters.get(name, "")

        def parameterAsOutputLayer(self, parameters, name, context):
            return parameters.get(name, "")

    alg = Algorithm()
    params = {
        alg.OUTPUT_RASTER: str(tmp_path / "coverage.tif"),
        alg.OUTPUT_REPORT_CSV: str(tmp_path / "coverage.csv"),
        alg.OUTPUT_REPORT_JSON: str(tmp_path / "coverage.json"),
        alg.OUTPUT_REPORT_HTML: str(tmp_path / "coverage.html"),
    }
    p = CoverageAnalysisParams(
        tx_lat=0.0,
        tx_lon=179.5,
        f_mhz=300.0,
        radius_km=1.0,
        grid_size=2,
        clutter_enabled=False,
        antenna_preset=0,
        tx_h=30.0,
        rx_h=10.0,
        tx_power=43.0,
        tx_gain=8.0,
        rx_gain=2.0,
        cable_loss=2.0,
        rx_sens=-100.0,
        antenna_az=None,
        antenna_bw_override=None,
        polarization=1,
        climate=1,
        n0=301.0,
        epsilon=15.0,
        sigma=0.005,
        time_pct=50.0,
        location_pct=50.0,
        situation_pct=50.0,
        front_back_db=25.0,
        downtilt_deg=0.0,
        h_pattern="",
        v_pattern="",
        clutter_grid=None,
        clutter_raster_path="",
        tx_clutter_override=None,
        rx_clutter_override=None,
    )
    writes = []

    monkeypatch.setattr(module, "extract_coverage_params", lambda *_args: p)
    monkeypatch.setattr(module, "ensure_dem_for_area", lambda *_args, **_kw: "dem.tif")
    class FakeElevationGrid:
        min_lat = -0.1
        max_lat = 0.1
        min_lon = 179.4
        max_lon = 179.6
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def close(self):
            pass
    monkeypatch.setattr(module, "ElevationGrid", lambda path: FakeElevationGrid())
    monkeypatch.setattr(module, "QgsRasterLayer", InvalidRasterLayer)
    def _fake_coverage_result(**_kw):
        from coverage_engine import CoverageResult
        return CoverageResult(
            prx_grid=np.array([[-80.0, -90.0]], dtype=np.float32),
            loss_grid=np.array([[100.0, 110.0]], dtype=np.float32),
            min_lat=-0.1,
            max_lat=0.1,
            min_lon=179.4,
            max_lon=179.6,
            itm_loss_grid=np.array([[100.0, 110.0]], dtype=np.float32),
            clutter_loss_grid=np.zeros((1, 2), dtype=np.float32),
            clutter_rx_db_grid=np.zeros((1, 2), dtype=np.float32),
        )
    monkeypatch.setattr(
        module,
        "compute_coverage",
        _fake_coverage_result,
    )
    monkeypatch.setattr(
        module,
        "build_coverage_report_payload_for_grid",
        lambda **_kw: ({"status": {"summary": "ok"}}, np.array([[-80.0]]), np.array([[True]]), None),
    )
    monkeypatch.setattr(module, "write_coverage_geotiff", lambda *args: None)
    monkeypatch.setattr(module, "report_coverage_results", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "write_report_csv", lambda path, payload: writes.append(("csv", path)))
    monkeypatch.setattr(module, "write_report_json", lambda path, payload: writes.append(("json", path)))
    monkeypatch.setattr(module, "write_report_html", lambda path, payload, title: writes.append(("html", path)))

    alg.processAlgorithm(params, object(), Feedback())

    assert writes == [
        ("csv", params[alg.OUTPUT_REPORT_CSV]),
        ("json", params[alg.OUTPUT_REPORT_JSON]),
        ("html", params[alg.OUTPUT_REPORT_HTML]),
    ]


def test_contour_merge_uses_only_successfully_clipped_tiles(monkeypatch, tmp_path):
    import NoWires.contour_pipeline as module

    tile_a = str(tmp_path / "tile_a.tif")
    tile_b = str(tmp_path / "tile_b.tif")
    merge_inputs = []

    class Dataset:
        pass

    def fake_warp(dest, src, **kwargs):
        if isinstance(src, list):
            merge_inputs.extend(src)
            return Dataset()
        if os.path.basename(src) == "tile_a.tif":
            return None
        return Dataset()

    monkeypatch.setattr(module, "required_tiles", lambda *_args, **_kw: ["a", "b"])
    monkeypatch.setattr(module, "download_tiles", lambda *_args, **_kw: [tile_a, tile_b])
    monkeypatch.setattr(module.gdal, "Warp", fake_warp)
    monkeypatch.setattr(module.gdal, "Open", lambda path: Dataset())

    module.download_and_merge_tiles(
        south=0.0,
        north=1.0,
        west=0.0,
        east=1.0,
        temp_dir=str(tmp_path),
        aoi_shp_path=str(tmp_path / "aoi.shp"),
        proxy_opener=None,
        feedback=Feedback(),
        progress=0.0,
        status_total=1.0,
    )

    assert merge_inputs == [str(tmp_path / "tile_b_clip.tif")]
