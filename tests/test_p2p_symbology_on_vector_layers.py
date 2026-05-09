# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify p2p_symbology functions apply correctly to real QgsVectorLayers."""

import os
import pytest

try:
    from qgis.core import (
        QgsApplication, QgsVectorLayer,
        QgsRuleBasedRenderer,
    )
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


@pytest.fixture(scope="module")
def qgis_app():
    from qgis.PyQt.QtCore import QCoreApplication
    QCoreApplication([])
    qgis = QgsApplication([], False)
    qgis.initQgis()
    yield qgis
    qgis.exitQgis()


def _create_polygon_gpkg(path):
    from osgeo import ogr, osr
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("fresnel_polygons", srs=srs, geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("type", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("blocked", ogr.OFTInteger))
    for ftype, blocked in [("fresnel_zone", 0), ("fresnel_violation_band_60pct", 0)]:
        feat = ogr.Feature(layer.GetLayerDefn())
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(8.0, 47.0)
        ring.AddPoint(8.05, 47.0)
        ring.AddPoint(8.05, 47.05)
        ring.AddPoint(8.0, 47.05)
        ring.AddPoint(8.0, 47.0)
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        feat.SetGeometry(poly)
        feat.SetField("type", ftype)
        feat.SetField("blocked", blocked)
        layer.CreateFeature(feat)
    ds = None


def _create_lines_gpkg(path, field_defs):
    """Create a simple lines GPKG. field_defs: list of (name, type_str)."""
    from osgeo import ogr, osr
    _TYPE_MAP = {"string": ogr.OFTString, "integer": ogr.OFTInteger}
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("lines", srs=srs, geom_type=ogr.wkbLineString)
    for fname, ftype_str in field_defs:
        layer.CreateField(ogr.FieldDefn(fname, _TYPE_MAP[ftype_str]))
    line = ogr.Geometry(ogr.wkbLineString)
    line.AddPoint(8.0, 47.0)
    line.AddPoint(8.05, 47.05)
    feat = ogr.Feature(layer.GetLayerDefn())
    feat.SetGeometry(line)
    for fname, ftype_str in field_defs:
        if ftype_str == "string":
            feat.SetField(fname, "terrain")
        elif ftype_str == "integer":
            feat.SetField(fname, 0)
    layer.CreateFeature(feat)
    ds = None


class TestFresnelPolygonSymbology:
    def test_apply_polygon_symbology_sets_renderer(self, qgis_app, tmp_path):
        from NoWires.p2p_symbology import apply_fresnel_polygon_symbology
        gpkg = str(tmp_path / "fresnel_poly.gpkg")
        _create_polygon_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "Fresnel Polygons", "ogr")
        assert layer.isValid(), "Layer not valid: {}".format(layer.error().summary())
        apply_fresnel_polygon_symbology(layer)
        renderer = layer.renderer()
        assert isinstance(renderer, QgsRuleBasedRenderer), \
            "Expected QgsRuleBasedRenderer, got {}".format(type(renderer).__name__)

    def test_polygon_renderer_has_type_rules(self, qgis_app, tmp_path):
        from NoWires.p2p_symbology import apply_fresnel_polygon_symbology
        gpkg = str(tmp_path / "fresnel_poly_rules.gpkg")
        _create_polygon_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "FP Rules", "ogr")
        assert layer.isValid()
        apply_fresnel_polygon_symbology(layer)
        renderer = layer.renderer()
        root = renderer.rootRule()
        labels = [r.label() for r in root.children()]
        assert "1st Fresnel Zone" in labels
        assert "60% Violation Band" in labels


class TestFresnelLinesSymbology:
    def test_apply_lines_symbology_sets_renderer(self, qgis_app, tmp_path):
        from NoWires.p2p_symbology import apply_fresnel_lines_symbology
        gpkg = str(tmp_path / "fresnel_lines.gpkg")
        _create_lines_gpkg(gpkg, [("type", "string"), ("blocked", "integer")])
        layer = QgsVectorLayer(gpkg, "Fresnel Lines", "ogr")
        assert layer.isValid()
        apply_fresnel_lines_symbology(layer)
        renderer = layer.renderer()
        assert isinstance(renderer, QgsRuleBasedRenderer)

    def test_lines_renderer_has_expected_rules(self, qgis_app, tmp_path):
        from NoWires.p2p_symbology import apply_fresnel_lines_symbology
        gpkg = str(tmp_path / "fresnel_lines_rules.gpkg")
        _create_lines_gpkg(gpkg, [("type", "string"), ("blocked", "integer")])
        layer = QgsVectorLayer(gpkg, "FL Rules", "ogr")
        assert layer.isValid()
        apply_fresnel_lines_symbology(layer)
        renderer = layer.renderer()
        root = renderer.rootRule()
        labels = [r.label() for r in root.children()]
        assert "Terrain" in labels
        assert "Line of Sight" in labels


class TestProfileLineSymbology:
    def test_apply_profile_line_symbology_sets_renderer(self, qgis_app, tmp_path):
        from NoWires.p2p_symbology import apply_profile_line_symbology
        gpkg = str(tmp_path / "profile_line.gpkg")
        _create_lines_gpkg(gpkg, [("mode", "integer"), ("mode_name", "string")])
        layer = QgsVectorLayer(gpkg, "Profile Line", "ogr")
        assert layer.isValid()
        apply_profile_line_symbology(layer)
        renderer = layer.renderer()
        assert isinstance(renderer, QgsRuleBasedRenderer)

    def test_profile_line_renderer_has_mode_rules(self, qgis_app, tmp_path):
        from NoWires.p2p_symbology import apply_profile_line_symbology
        gpkg = str(tmp_path / "profile_modes.gpkg")
        _create_lines_gpkg(gpkg, [("mode", "integer"), ("mode_name", "string")])
        layer = QgsVectorLayer(gpkg, "PL Modes", "ogr")
        assert layer.isValid()
        apply_profile_line_symbology(layer)
        renderer = layer.renderer()
        root = renderer.rootRule()
        labels = [r.label() for r in root.children()]
        assert "LOS" in labels
        assert "Diffraction" in labels