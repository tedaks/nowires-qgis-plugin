# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify contour symbology applies correctly to a real QgsVectorLayer."""

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


def _create_contour_gpkg(path):
    from osgeo import ogr, osr
    driver = ogr.GetDriverByName("GPKG")
    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("contours", srs=srs, geom_type=ogr.wkbLineString)
    layer.CreateField(ogr.FieldDefn("ELEV", ogr.OFTReal))
    for elev in [100, 200, 300, 400, 500]:
        feat = ogr.Feature(layer.GetLayerDefn())
        line = ogr.Geometry(ogr.wkbLineString)
        line.AddPoint(8.0, 47.0, elev)
        line.AddPoint(8.1, 47.05, elev)
        feat.SetGeometry(line)
        feat.SetField("ELEV", float(elev))
        layer.CreateFeature(feat)
    ds = None


class TestContourSymbology:
    def test_apply_contour_symbology_sets_renderer(self, qgis_app, tmp_path):
        from NoWires.contour_symbology import apply_contour_symbology
        gpkg = str(tmp_path / "contours.gpkg")
        _create_contour_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "Contours", "ogr")
        assert layer.isValid(), "Layer not valid: {}".format(layer.error().summary())
        from qgis.PyQt.QtGui import QColor
        color = QColor(204, 119, 0, 204)
        apply_contour_symbology(layer, color, interval=10)
        renderer = layer.renderer()
        assert renderer is not None
        assert isinstance(renderer, QgsRuleBasedRenderer), \
            "Expected QgsRuleBasedRenderer, got {}".format(type(renderer).__name__)

    def test_contour_renderer_has_index_and_normal_rules(self, qgis_app, tmp_path):
        from NoWires.contour_symbology import apply_contour_symbology
        gpkg = str(tmp_path / "contours_rules.gpkg")
        _create_contour_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "Contours", "ogr")
        assert layer.isValid()
        from qgis.PyQt.QtGui import QColor
        apply_contour_symbology(layer, QColor(204, 119, 0, 204), interval=10)
        renderer = layer.renderer()
        root = renderer.rootRule()
        child_count = root.children()
        assert len(child_count) >= 2, \
            "Expected >= 2 rules (index + normal), got {}".format(len(child_count))

    def test_contour_labels_enabled(self, qgis_app, tmp_path):
        from NoWires.contour_symbology import apply_contour_symbology
        gpkg = str(tmp_path / "contours_labels.gpkg")
        _create_contour_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "Contours", "ogr")
        assert layer.isValid()
        from qgis.PyQt.QtGui import QColor
        apply_contour_symbology(layer, QColor(204, 119, 0, 204), interval=10)
        assert layer.labelsEnabled(), "Labels should be enabled after applying symbology"

    def test_contour_labeling_is_simple_labeling(self, qgis_app, tmp_path):
        from NoWires.contour_symbology import apply_contour_symbology
        from qgis.core import QgsVectorLayerSimpleLabeling
        gpkg = str(tmp_path / "contours_simple.gpkg")
        _create_contour_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "Contours", "ogr")
        assert layer.isValid()
        from qgis.PyQt.QtGui import QColor
        apply_contour_symbology(layer, QColor(204, 119, 0, 204), interval=10)
        labeling = layer.labeling()
        assert isinstance(labeling, QgsVectorLayerSimpleLabeling)