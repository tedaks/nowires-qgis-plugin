# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify dem_downloader QgsGeometry operations work correctly in QGIS 4."""

import os
import pytest

try:
    from qgis.core import QgsApplication, QgsGeometry, QgsPointXY, QgsRectangle
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


class TestDemDownloaderGeometry:
    def test_qgsgeometry_from_rect(self, qgis_app):
        rect = QgsRectangle(8.0, 47.0, 9.0, 48.0)
        geom = QgsGeometry.fromRect(rect)
        assert not geom.isNull()
        assert not geom.isEmpty()

    def test_qgsgeometry_from_polygon_xy(self, qgis_app):
        points = [
            QgsPointXY(8.0, 47.0),
            QgsPointXY(9.0, 47.0),
            QgsPointXY(9.0, 48.0),
            QgsPointXY(8.0, 48.0),
        ]
        poly = QgsGeometry.fromPolygonXY([points])
        assert not poly.isNull()
        assert not poly.isEmpty()

    def test_intersection_non_overlapping(self, qgis_app):
        aoi = QgsGeometry.fromRect(QgsRectangle(8.0, 47.0, 9.0, 48.0))
        tile = QgsGeometry.fromPolygonXY([
            [QgsPointXY(10.0, 49.0), QgsPointXY(11.0, 49.0),
             QgsPointXY(11.0, 50.0), QgsPointXY(10.0, 50.0)]
        ])
        inter = tile.intersection(aoi)
        assert inter.isEmpty()

    def test_intersection_overlapping(self, qgis_app):
        aoi = QgsGeometry.fromRect(QgsRectangle(8.0, 47.0, 9.0, 48.0))
        tile = QgsGeometry.fromPolygonXY([
            [QgsPointXY(8.0, 47.0), QgsPointXY(9.0, 47.0),
             QgsPointXY(9.0, 48.0), QgsPointXY(8.0, 48.0)]
        ])
        inter = tile.intersection(aoi)
        assert not inter.isEmpty()

    def test_required_tiles_with_known_area(self, qgis_app):
        from NoWires.dem_downloader import required_tiles
        tiles = required_tiles(47.0, 48.0, 8.0, 9.0)
        assert len(tiles) > 0
        for name in tiles:
            assert name.startswith("Copernicus_DSM_COG_10_")

    def test_required_tiles_empty_for_zero_area(self, qgis_app):
        from NoWires.dem_downloader import required_tiles
        tiles = required_tiles(47.0, 47.0, 8.0, 8.0)
        assert len(tiles) == 0