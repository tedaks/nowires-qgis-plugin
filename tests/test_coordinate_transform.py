# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify QgsCoordinateTransform works correctly with QGIS 4 runtime."""

import os
import pytest

try:
    from qgis.core import (
        QgsApplication, QgsCoordinateReferenceSystem,
        QgsCoordinateTransform, QgsPointXY, QgsProject,
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
    QCoreApplication()
    qgis = QgsApplication()
    qgis.initQgis()
    yield qgis
    qgis.exitQgis()


class TestCoordinateTransform:
    def test_4326_to_3857(self, qgis_app):
        src_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        dst_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        assert src_crs.isValid(), "EPSG:4326 CRS is not valid"
        assert dst_crs.isValid(), "EPSG:3857 CRS is not valid"
        transform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
        point = QgsPointXY(8.0, 47.0)
        result = transform.transform(point)
        assert abs(result.x() - 890555.85) < 100, \
            "EPSG:3857 X too far off: {}".format(result.x())
        assert abs(result.y() - 5922072.0) < 100, \
            "EPSG:3857 Y too far off: {}".format(result.y())

    def test_3857_to_4326(self, qgis_app):
        src_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        dst_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        assert src_crs.isValid()
        assert dst_crs.isValid()
        transform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
        web_merc = QgsPointXY(890555.85, 5922072.0)
        result = transform.transform(web_merc)
        assert abs(result.x() - 8.0) < 0.01, \
            "Round-trip lon too far off: {}".format(result.x())
        assert abs(result.y() - 47.0) < 0.01, \
            "Round-trip lat too far off: {}".format(result.y())

    def test_4326_identity(self, qgis_app):
        crs = QgsCoordinateReferenceSystem("EPSG:4326")
        assert crs.isValid()
        transform = QgsCoordinateTransform(crs, crs, QgsProject.instance())
        point = QgsPointXY(8.0, 47.0)
        result = transform.transform(point)
        assert abs(result.x() - 8.0) < 1e-10
        assert abs(result.y() - 47.0) < 1e-10

    def test_batch_algorithm_coordinate_transform_pattern(self, qgis_app):
        src_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        dst_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
        point = QgsPointXY(1113194.9, 6800125.5)
        result = transform.transform(point)
        assert -90 <= result.y() <= 90, "Latitude out of range: {}".format(result.y())
        assert -180 <= result.x() <= 180, "Longitude out of range: {}".format(result.x())