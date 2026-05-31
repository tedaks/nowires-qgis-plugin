# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""pytest configuration.

When tests are run via ``pytest tests/`` from the repo root (no QGIS
installed), the osgeo and qgis modules are not available. This conftest:

1. Delegates QGIS/osgeo/PyQt mock setup to ``_qgis_mocks``.
2. Delegates NoWires package registration to ``_qgis_mocks``.
3. Provides a session-scoped ``qgis_app`` fixture for integration tests.

When a real QGIS runtime is available (QGIS_PREFIX_PATH set or qgis.core
importable), all mocking is skipped so integration tests use the real QGIS.
"""

import os
import pathlib
import sys

# Auto-detect PROJ data directory when running against a QGIS bundle.
# Must happen before any qgis.core import triggers PROJ initialisation.
_qgis_prefix = os.environ.get("QGIS_PREFIX_PATH", "")
if _qgis_prefix and not os.environ.get("PROJ_DATA"):
    _proj_candidate = pathlib.Path(_qgis_prefix).parent / "Resources" / "qgis" / "proj"
    if (_proj_candidate / "proj.db").exists():
        os.environ["PROJ_DATA"] = str(_proj_candidate)
        os.environ.setdefault("PROJ_LIB", str(_proj_candidate))

sys.path.insert(0, os.path.dirname(__file__))
from _qgis_mocks import install_qgis_mocks, register_nowires_package, HAS_REAL_GDAL

import numpy as np
import pytest

install_qgis_mocks()
register_nowires_package()

if HAS_REAL_GDAL:
    from osgeo import gdal as _gdal
    _gdal.UseExceptions()

_DEM_DOWNLOADER_IMPORTERS = [
    "NoWires.algorithm.batch",
    "NoWires.algorithm.coverage",
    "NoWires.algorithm.coverage_comparison",
    "NoWires.p2p.compute",
]


@pytest.fixture
def patch_dem_download(monkeypatch, tmp_path):
    """Patch ensure_dem_for_area in the source module and all importers.

    Algorithm modules capture ``ensure_dem_for_area`` at import time via
    ``from NoWires.dem_downloader import ensure_dem_for_area``, so patching
    only the source module is not enough — each importer's namespace must
    also be updated.
    """
    from NoWires import dem_downloader

    dem_path = str(tmp_path / "mock_dem.tif")
    _mock_return = dem_path

    def _mock_ensure_dem_for_area(*args, **kwargs):
        return _mock_return

    monkeypatch.setattr(dem_downloader, "ensure_dem_for_area", _mock_ensure_dem_for_area)
    for module_name in _DEM_DOWNLOADER_IMPORTERS:
        try:
            mod = sys.modules.get(module_name)
            if mod is not None and hasattr(mod, "ensure_dem_for_area"):
                monkeypatch.setattr(mod, "ensure_dem_for_area", _mock_ensure_dem_for_area)
        except Exception:
            pass

    return dem_path


@pytest.fixture
def create_synthetic_dem():
    """Fixture factory returning a callable that creates a synthetic DEM GeoTIFF.

    Returns a function that creates a GeoTIFF filled with constant elevation
    values, suitable for algorithm integration tests.
    """
    def _create(path, south, north, west, east, nx=50, ny=50):
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
    return _create


@pytest.fixture(scope="session")
def qgis_app():
    """Session-scoped QgsApplication for integration tests.

    Qt6 only allows one QApplication per process.  Module-scoped fixtures
    that create/destroy QgsApplication cause segfaults, so we create a
    single instance for the entire test session.
    """
    from qgis.core import QgsApplication
    app = QgsApplication([], True)
    app.initQgis()
    yield app
    app.exitQgis()