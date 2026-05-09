# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify p2p_outputs GeoPackage/vector layers load correctly in QGIS."""

import os
import pytest
import numpy as np

try:
    from qgis.core import QgsVectorLayer, QgsWkbTypes
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


def _write_profile_line(path, srs):
    from NoWires.p2p_outputs import write_profile_line
    from NoWires.radio import ITMResult
    result = ITMResult(loss_db=120.5, mode=1, warnings=0)
    dist_m = 5000.0
    write_profile_line(path, srs, 47.0, 8.0, 47.05, 8.05, dist_m, result)


def _write_fresnel_zone(poly_path, lines_path, srs):
    from NoWires.p2p_outputs import write_fresnel_zone
    distances = np.array([0.0, 2500.0, 5000.0])
    terrain_bulge = np.array([300.0, 350.0, 320.0])
    los_h = np.array([400.0, 380.0, 360.0])
    fresnel_r = np.array([10.0, 15.0, 10.0])
    dist_m = 5000.0
    write_fresnel_zone(
        poly_path, lines_path, srs, 47.0, 8.0, 47.05, 8.05,
        distances, terrain_bulge, los_h, fresnel_r, dist_m,
    )


class TestProfileLineVectorLayer:
    def test_profile_line_gpkg_loads(self, qgis_app, tmp_path):
        gpkg = str(tmp_path / "profile.gpkg")
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        _write_profile_line(gpkg, srs)
        layer = QgsVectorLayer(gpkg, "profile", "ogr")
        assert layer.isValid(), "Profile line GPKG did not load: {}".format(
            "layer load failed")
        assert layer.featureCount() == 1
        assert layer.fields().lookupField("distance") >= 0
        assert layer.fields().lookupField("loss_db") >= 0
        assert layer.fields().lookupField("mode") >= 0
        assert layer.fields().lookupField("mode_name") >= 0

    def test_profile_line_geometry_is_linestring(self, qgis_app, tmp_path):
        gpkg = str(tmp_path / "profile_geom.gpkg")
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        _write_profile_line(gpkg, srs)
        layer = QgsVectorLayer(gpkg, "profile", "ogr")
        assert layer.isValid()
        ft = next(layer.getFeatures())
        assert ft.geometry() is not None
        assert ft.geometry().wkbType() in (
            QgsWkbTypes.Type.LineString, QgsWkbTypes.Type.LineStringZ,
            QgsWkbTypes.Type.LineStringM, QgsWkbTypes.Type.LineStringZM,
        )


class TestFresnelZoneVectorLayers:
    def test_fresnel_polygon_gpkg_loads(self, qgis_app, tmp_path):
        poly_gpkg = str(tmp_path / "fresnel_poly.gpkg")
        lines_gpkg = str(tmp_path / "fresnel_lines.gpkg")
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        _write_fresnel_zone(poly_gpkg, lines_gpkg, srs)
        layer = QgsVectorLayer(poly_gpkg, "fresnel", "ogr")
        assert layer.isValid(), "Fresnel polygon GPKG did not load: {}".format(
            "layer load failed")
        assert layer.featureCount() == 2
        for ft in layer.getFeatures():
            assert ft.attribute("type") is not None
            assert ft.attribute("blocked") is not None

    def test_fresnel_polygon_geometry_type(self, qgis_app, tmp_path):
        poly_gpkg = str(tmp_path / "fresnel_poly2.gpkg")
        lines_gpkg = str(tmp_path / "fresnel_lines2.gpkg")
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        _write_fresnel_zone(poly_gpkg, lines_gpkg, srs)
        layer = QgsVectorLayer(poly_gpkg, "fresnel", "ogr")
        assert layer.isValid()
        assert layer.wkbType() in (
            QgsWkbTypes.Type.Polygon, QgsWkbTypes.Type.PolygonZ,
            QgsWkbTypes.Type.MultiPolygon, QgsWkbTypes.Type.MultiPolygonZ,
        )

    def test_fresnel_lines_gpkg_loads(self, qgis_app, tmp_path):
        poly_gpkg = str(tmp_path / "fresnel_poly3.gpkg")
        lines_gpkg = str(tmp_path / "fresnel_lines3.gpkg")
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        _write_fresnel_zone(poly_gpkg, lines_gpkg, srs)
        layer = QgsVectorLayer(lines_gpkg, "fresnel_lines", "ogr")
        assert layer.isValid(), "Fresnel lines GPKG did not load: {}".format(
            "layer load failed")
        assert layer.featureCount() == 2

    def test_fresnel_lines_geometry_is_linestring(self, qgis_app, tmp_path):
        poly_gpkg = str(tmp_path / "fresnel_poly4.gpkg")
        lines_gpkg = str(tmp_path / "fresnel_lines4.gpkg")
        from osgeo import osr
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        _write_fresnel_zone(poly_gpkg, lines_gpkg, srs)
        layer = QgsVectorLayer(lines_gpkg, "fresnel_lines", "ogr")
        assert layer.isValid()
        assert layer.wkbType() in (
            QgsWkbTypes.Type.LineString, QgsWkbTypes.Type.LineStringZ,
            QgsWkbTypes.Type.MultiLineString, QgsWkbTypes.Type.MultiLineStringZ,
        )