# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify processing_utils.queue_layer_for_loading works with real QgsProcessingContext."""

import os
import pytest
import numpy as np

try:
    from qgis.core import (
        QgsProcessingContext, QgsRasterLayer,
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


def _make_geotiff(path):
    from NoWires.raster_io import write_geotiff
    grid = np.full((4, 4), -50.0, dtype=np.float32)
    write_geotiff(path, grid, 47.0, 47.01, 8.0, 8.01)


class TestQueueLayerForLoading:
    def test_queue_valid_layer(self, qgis_app, tmp_path):
        from NoWires.processing_utils import queue_layer_for_loading
        tif = str(tmp_path / "test.tif")
        _make_geotiff(tif)
        context = QgsProcessingContext()
        layer = QgsRasterLayer(tif, "Test Layer")
        assert layer.isValid()
        result = queue_layer_for_loading(context, layer, "Test Layer")
        assert result is True

    def test_queue_adds_layer_to_temp_store(self, qgis_app, tmp_path):
        from NoWires.processing_utils import queue_layer_for_loading
        tif = str(tmp_path / "test_store.tif")
        _make_geotiff(tif)
        context = QgsProcessingContext()
        layer = QgsRasterLayer(tif, "Store Test")
        assert layer.isValid()
        queue_layer_for_loading(context, layer, "Store Test")
        store = context.temporaryLayerStore()
        assert store is not None
        added = store.mapLayers()
        assert layer.id() in added or len(added) > 0

    def test_queue_registers_completion_detail(self, qgis_app, tmp_path):
        from NoWires.processing_utils import queue_layer_for_loading
        tif = str(tmp_path / "test_complete.tif")
        _make_geotiff(tif)
        context = QgsProcessingContext()
        layer = QgsRasterLayer(tif, "Completion Test")
        assert layer.isValid()
        queue_layer_for_loading(context, layer, "Completion Test")
        layers_to_load = context.layersToLoadOnCompletion()
        assert len(layers_to_load) > 0

    def test_queue_returns_false_for_invalid_layer(self, qgis_app):
        from NoWires.processing_utils import queue_layer_for_loading
        context = QgsProcessingContext()
        layer = QgsRasterLayer("/nonexistent/path.tif", "Invalid")
        result = queue_layer_for_loading(context, layer, "Invalid")
        assert result is False

    def test_queue_returns_false_for_none(self, qgis_app):
        from NoWires.processing_utils import queue_layer_for_loading
        context = QgsProcessingContext()
        result = queue_layer_for_loading(context, None, "None Layer")
        assert result is False