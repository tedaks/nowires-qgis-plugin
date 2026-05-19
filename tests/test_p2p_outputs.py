# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for p2p_outputs OGR write functions.

These tests require a QGIS/GDAL runtime because write_profile_line and
write_fresnel_zone use OGR directly to create vector datasets.
"""


import pytest

try:
    from osgeo import ogr, osr
    _HAS_GDAL = True
except ImportError:
    _HAS_GDAL = False

pytestmark = [
    pytest.mark.skipif(not _HAS_GDAL, reason="OGR/GDAL not available"),
    pytest.mark.qgis_integration,
]

from p2p.outputs import write_profile_line, write_fresnel_zone
from radio import PROP_MODE_NAMES
from unittest.mock import MagicMock

import numpy as np


def _make_srs():
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


def _mock_result(loss_db=120.0, mode=1):
    r = MagicMock()
    r.loss_db = loss_db
    r.mode = mode
    return r


class TestWriteProfileLine:
    def test_creates_geopackage_with_line(self, tmp_path):
        path = str(tmp_path / "profile.gpkg")
        srs = _make_srs()
        result = _mock_result(loss_db=135.7, mode=1)
        write_profile_line(
            path, srs, 47.0, 8.0, 47.1, 8.1, 12000.0, result, itm_loss_db=135.7,
        )
        ds = ogr.Open(path)
        assert ds is not None
        layer = ds.GetLayer(0)
        assert layer.GetFeatureCount() == 1
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsDouble("distance") == 12000.0
        assert feat.GetFieldAsDouble("loss_db") == 135.7
        assert feat.GetFieldAsInteger("mode") == 1
        assert feat.GetFieldAsString("mode_name") == PROP_MODE_NAMES.get(1, "Unknown")
        ds = None

    def test_uses_result_loss_when_itm_loss_none(self, tmp_path):
        path = str(tmp_path / "profile2.gpkg")
        srs = _make_srs()
        result = _mock_result(loss_db=98.5, mode=1)
        write_profile_line(
            path, srs, 47.0, 8.0, 47.1, 8.1, 10000.0, result,
        )
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsDouble("loss_db") == 98.5
        ds = None

    def test_overwrites_existing_file(self, tmp_path):
        path = str(tmp_path / "profile_overwrite.gpkg")
        srs = _make_srs()
        result = _mock_result(loss_db=100.0, mode=1)
        write_profile_line(path, srs, 47.0, 8.0, 47.1, 8.1, 10000.0, result)
        result2 = _mock_result(loss_db=110.0, mode=2)
        write_profile_line(path, srs, 47.0, 8.0, 47.1, 8.1, 10000.0, result2)
        ds = ogr.Open(path)
        layer = ds.GetLayer(0)
        feat = layer.GetNextFeature()
        assert feat.GetFieldAsDouble("loss_db") == 110.0
        ds = None


class TestWriteFresnelZone:
    def _make_inputs(self, n=10):
        distances = np.linspace(0, 12000, n, dtype=np.float64)
        terrain_bulge = np.linspace(5, 50, n, dtype=np.float64)
        los_h = np.linspace(35, 30, n, dtype=np.float64)
        fresnel_r = np.full(n, 12.0, dtype=np.float64)
        return distances, terrain_bulge, los_h, fresnel_r

    def test_creates_polygon_and_lines(self, tmp_path):
        poly_path = str(tmp_path / "fresnel_poly.gpkg")
        lines_path = str(tmp_path / "fresnel_lines.gpkg")
        srs = _make_srs()
        distances, terrain_bulge, los_h, fresnel_r = self._make_inputs()
        write_fresnel_zone(
            poly_path, lines_path, srs,
            47.0, 8.0, 47.1, 8.1,
            distances, terrain_bulge, los_h, fresnel_r, 12000.0,
        )
        poly_ds = ogr.Open(poly_path)
        assert poly_ds is not None
        poly_layer = poly_ds.GetLayer(0)
        feat = poly_layer.GetNextFeature()
        assert feat.GetFieldAsString("type") == "fresnel_zone"
        poly_ds = None

        lines_ds = ogr.Open(lines_path)
        assert lines_ds is not None
        lines_ds = None

    def test_fresnel_vertices_count(self, tmp_path):
        poly_path = str(tmp_path / "fresnel_poly2.gpkg")
        lines_path = str(tmp_path / "fresnel_lines2.gpkg")
        srs = _make_srs()
        n = 5
        distances = np.linspace(0, 5000, n, dtype=np.float64)
        terrain_bulge = np.full(n, 10.0, dtype=np.float64)
        los_h = np.full(n, 30.0, dtype=np.float64)
        fresnel_r = np.full(n, 8.0, dtype=np.float64)
        write_fresnel_zone(
            poly_path, lines_path, srs,
            47.0, 8.0, 47.1, 8.1,
            distances, terrain_bulge, los_h, fresnel_r, 5000.0,
        )
        poly_ds = ogr.Open(poly_path)
        layer = poly_ds.GetLayer(0)
        assert layer.GetFeatureCount() >= 1
        feat = layer.GetNextFeature()
        geom = feat.GetGeometryRef()
        ring = geom.GetGeometryRef(0)
        assert ring.GetPointCount() == 2 * n + 1
        poly_ds = None