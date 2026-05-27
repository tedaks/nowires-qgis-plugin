# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""QGIS integration test: advanced clutter mode registration."""

import os

import pytest

try:
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


class TestAdvancedClutterIntegration:
    def test_clutter_model_enum_contains_advanced(self, qgis_app):
        from NoWires.clutter import CLUTTER_MODEL_OPTIONS
        assert any("advanced" in opt.lower() for opt in CLUTTER_MODEL_OPTIONS)

    def test_clutter_context_knows_advanced_model(self, qgis_app):
        from NoWires.clutter.context import _VALID_MODELS
        assert "advanced" in _VALID_MODELS
        assert "simple" in _VALID_MODELS
