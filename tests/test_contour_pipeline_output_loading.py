# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify contour_pipeline raster layer loading and DEM elevation configuration."""

import os
import pytest
import numpy as np

try:
    from qgis.core import (
        QgsRasterLayer, Qgis,
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


def _write_dem_geotiff(path):
    from NoWires.raster_io import write_geotiff
    grid = np.random.uniform(100, 2000, size=(20, 20)).astype(np.float32)
    write_geotiff(path, grid, 47.0, 47.1, 8.0, 8.1)


class TestDemOutputLoading:
    def test_load_dem_output_elevation_properties(self, qgis_app, tmp_path):
        tif = str(tmp_path / "dem_elev.tif")
        _write_dem_geotiff(tif)
        layer = QgsRasterLayer(tif, "Test DEM")
        assert layer.isValid(), "DEM layer not valid: {}".format("layer load failed")
        elev_props = layer.elevationProperties()
        assert elev_props is not None
        elev_props.setEnabled(True)
        elev_props.setMode(Qgis.RasterElevationMode.RepresentsElevationSurface)
        elev_props.setBandNumber(1)
        assert elev_props.isEnabled()
        assert layer.bandCount() >= 1

    def test_load_dem_output_band_count(self, qgis_app, tmp_path):
        tif = str(tmp_path / "dem_bands.tif")
        _write_dem_geotiff(tif)
        layer = QgsRasterLayer(tif, "Test DEM Bands")
        assert layer.isValid()
        assert layer.bandCount() == 1

    def test_load_dem_output_extent(self, qgis_app, tmp_path):
        tif = str(tmp_path / "dem_extent.tif")
        _write_dem_geotiff(tif)
        layer = QgsRasterLayer(tif, "Test DEM Extent")
        assert layer.isValid()
        extent = layer.extent()
        assert extent.xMinimum() < extent.xMaximum()
        assert extent.yMinimum() < extent.yMaximum()


class TestOverlayRasterLoading:
    def test_raster_layer_blend_mode(self, qgis_app, tmp_path):
        from qgis.PyQt.QtGui import QPainter
        tif = str(tmp_path / "overlay_blend.tif")
        _write_dem_geotiff(tif)
        layer = QgsRasterLayer(tif, "Overlay Test")
        assert layer.isValid()
        blend_mode = QPainter.CompositionMode.CompositionMode_ColorDodge
        layer.setBlendMode(blend_mode)
        assert layer.blendMode() == blend_mode

    def test_raster_layer_opacity(self, qgis_app, tmp_path):
        tif = str(tmp_path / "overlay_opacity.tif")
        _write_dem_geotiff(tif)
        layer = QgsRasterLayer(tif, "Opacity Test")
        assert layer.isValid()
        layer.setOpacity(0.7)
        assert abs(layer.opacity() - 0.7) < 0.01