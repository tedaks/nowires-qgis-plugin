# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify 3D terrain configuration APIs work with QGIS 4 runtime."""

import os
import pytest

try:
    from qgis.core import QgsApplication, QgsVectorLayer, Qgis
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
    qgis = QgsApplication([], True)
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
    for elev in [100, 200, 300]:
        feat = ogr.Feature(layer.GetLayerDefn())
        line = ogr.Geometry(ogr.wkbLineString)
        line.AddPoint(8.0, 47.0, elev)
        line.AddPoint(8.1, 47.05, elev)
        feat.SetGeometry(line)
        feat.SetField("ELEV", float(elev))
        layer.CreateFeature(feat)
    ds = None


class Test3DTerrainConfiguration:
    def test_configure_contours_for_3d(self, qgis_app, tmp_path):
        from NoWires.three_d import configure_contours_for_3d
        gpkg = str(tmp_path / "contours_3d.gpkg")
        _create_contour_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "3D Contours", "ogr")
        assert layer.isValid()
        result = configure_contours_for_3d(layer, elevation_field="ELEV")
        assert result is not None or result is layer
        elev_props = layer.elevationProperties()
        assert elev_props is not None
        if hasattr(elev_props, 'clamping'):
            assert elev_props.clamping() == Qgis.AltitudeClamping.Terrain
        if hasattr(elev_props, 'binding'):
            assert elev_props.binding() == Qgis.AltitudeBinding.Vertex

    def test_vector_layer_elevation_properties(self, qgis_app, tmp_path):
        gpkg = str(tmp_path / "contours_elev.gpkg")
        _create_contour_gpkg(gpkg)
        layer = QgsVectorLayer(gpkg, "Elev Contours", "ogr")
        assert layer.isValid()
        elev_props = layer.elevationProperties()
        assert elev_props is not None
        elev_props.setEnabled(True)
        assert elev_props.isEnabled()
        elev_props.setClamping(Qgis.AltitudeClamping.Terrain)
        elev_props.setBinding(Qgis.AltitudeBinding.Vertex)

    def test_qgis_scene_mode_enum(self, qgis_app):
        assert hasattr(Qgis, 'SceneMode')
        assert hasattr(Qgis.SceneMode, 'Local')
        assert hasattr(Qgis.SceneMode, 'Globe')

    def test_altitude_clamping_enum(self, qgis_app):
        assert hasattr(Qgis, 'AltitudeClamping')
        assert hasattr(Qgis.AltitudeClamping, 'Terrain')

    def test_altitude_binding_enum(self, qgis_app):
        assert hasattr(Qgis, 'AltitudeBinding')
        assert hasattr(Qgis.AltitudeBinding, 'Vertex')

    def test_raster_elevation_mode_enum(self, qgis_app):
        assert hasattr(Qgis, 'RasterElevationMode')
        assert hasattr(Qgis.RasterElevationMode, 'RepresentsElevationSurface')

    def test_qgs_raster_dem_terrain_provider_importable(self, qgis_app):
        try:
            from qgis.core import QgsRasterDemTerrainProvider
            assert QgsRasterDemTerrainProvider is not None
        except ImportError:
            pytest.skip("QgsRasterDemTerrainProvider not available in this QGIS build")