# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""QGIS integration tests — require a real QGIS runtime.

These tests are skipped unless QGIS_PREFIX_PATH is set.
Run them via:
    pytest tests/test_qgis_integration.py -v
or:
    QGIS_PREFIX_PATH=/usr QGIS_PYTHON_PATH=/usr/lib/qisp pytest tests/test_qgis_integration.py -v

Alternatively, select them by marker:
    pytest -m qgis_integration -v
"""
import os
import tempfile
import pytest
import numpy as np

# Gate: skip entire module if QGIS is not available
try:
    from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
    from qgis.PyQt.QtCore import QCoreApplication
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
    """Bootstrap a QgsApplication for the test module."""
    QCoreApplication([])  # noqa: F841
    qgis = QgsApplication([], False)
    qgis.initQgis()
    yield qgis
    qgis.exitQgis()


@pytest.fixture
def processing_context(qgis_app):
    return QgsProcessingContext()


@pytest.fixture
def feedback():
    return QgsProcessingFeedback()


class TestProviderRegistryIntegration:
    def test_provider_registers_in_processing_registry(self, qgis_app):
        from NoWires.provider import NoWiresProvider
        registry = QgsApplication.processingRegistry()
        provider = NoWiresProvider()
        added = registry.addProvider(provider)
        assert added
        retrieved = registry.providerById("nowires")
        assert retrieved is not None
        registry.removeProvider("nowires")

    def test_all_algorithms_are_executable(self, qgis_app):
        from NoWires.provider import NoWiresProvider
        provider = NoWiresProvider()
        provider.loadAlgorithms()
        for alg in provider.algorithms():
            assert alg.name() is not None
            instance = alg.createInstance()
            assert instance.name() == alg.name()


class TestCoverageStyleIntegration:
    def test_apply_coverage_style_on_real_raster_layer(self, qgis_app):
        """Verify apply_coverage_style works on a real QgsRasterLayer."""
        from coverage_palette import apply_coverage_style
        from osgeo import gdal, osr
        tmp = tempfile.mktemp(suffix=".tif")
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(tmp, 4, 4, 1, gdal.GDT_Float32)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())
        ds.SetGeoTransform([0.0, 0.01, 0, 0.01, 0, -0.01])
        band = ds.GetRasterBand(1)
        band.WriteArray(np.full((4, 4), -70.0, dtype=np.float32))
        band.FlushCache()
        ds = None

        from qgis.core import QgsRasterLayer
        layer = QgsRasterLayer(tmp, "Test Coverage")
        assert layer.isValid(), "Layer not valid: {}".format(layer.error().summary())
        apply_coverage_style(layer)
        assert layer.renderer() is not None

        os.unlink(tmp)


class TestWriteGeotiffIntegration:
    def test_write_geotiff_produces_valid_raster(self, qgis_app):
        from raster_io import write_geotiff
        tmp = tempfile.mktemp(suffix=".tif")
        grid = np.full((10, 10), -80.0, dtype=np.float32)
        write_geotiff(tmp, grid, 0.0, 0.1, 0.0, 0.1)

        from osgeo import gdal
        ds = gdal.Open(tmp)
        assert ds is not None
        assert ds.RasterXSize == 10
        assert ds.RasterYSize == 10
        ds = None
        os.unlink(tmp)
