# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for tile_download_base clip_and_merge_tiles with synthetic GeoTIFF fixtures."""

import os

import numpy as np
import pytest

try:
    from osgeo import gdal, osr
    from unittest.mock import MagicMock
    _REAL_GDAL = not isinstance(gdal, MagicMock)
except ImportError:
    _REAL_GDAL = False

pytestmark = pytest.mark.skipif(not _REAL_GDAL, reason="Real GDAL not available (mocked by conftest)")

from NoWires.tile_merge import clip_and_merge_tiles


class _Feedback:
    def __init__(self):
        self.messages = []
    def pushInfo(self, m):
        self.messages.append(m)
    def isCanceled(self):
        return False


def _create_synthetic_tile(path, south, north, west, east, value=100.0, nx=10, ny=10):
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, nx, ny, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds.SetProjection(srs.ExportToWkt())
    dx = (east - west) / nx
    dy = (north - south) / ny
    ds.SetGeoTransform([west, dx, 0, north, 0, -dy])
    data = np.full((ny, nx), value, dtype=np.float32)
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(-32768)
    band.FlushCache()
    ds = None


@pytest.mark.gdal_integration
class TestClipAndMergeTiles:
    def test_merges_two_tiles(self, tmp_path):
        t1 = str(tmp_path / "tile1.tif")
        t2 = str(tmp_path / "tile2.tif")
        _create_synthetic_tile(t1, -1.0, 0.0, 0.0, 1.0, value=10.0)
        _create_synthetic_tile(t2, 0.0, 1.0, 0.0, 1.0, value=20.0)

        fb = _Feedback()
        result = clip_and_merge_tiles(
            [t1, t2], south=-0.5, north=0.5, west=0.0, east=1.0,
            temp_dir=str(tmp_path), feedback=fb,
            nodata_value=-32768, aoi_prefix="test",
            merge_filename="merged.tif",
        )

        assert result is not None
        assert os.path.exists(result)
        ds = gdal.Open(result)
        assert ds is not None
        assert ds.RasterXSize > 0
        assert ds.RasterYSize > 0
        ds = None

    def test_empty_tile_list_returns_none(self, tmp_path):
        fb = _Feedback()
        result = clip_and_merge_tiles(
            [], south=0.0, north=1.0, west=0.0, east=1.0,
            temp_dir=str(tmp_path), feedback=fb,
            nodata_value=-32768, aoi_prefix="test",
            merge_filename="merged.tif",
        )
        assert result is None

    def test_cancel_stops_processing(self, tmp_path):
        t1 = str(tmp_path / "tile1.tif")
        _create_synthetic_tile(t1, -1.0, 0.0, 0.0, 1.0)

        class _CancelFeed:
            def isCanceled(self):
                return True
            def pushInfo(self, m):
                pass

        result = clip_and_merge_tiles(
            [t1], south=-0.5, north=0.5, west=0.0, east=1.0,
            temp_dir=str(tmp_path), feedback=_CancelFeed(),
            nodata_value=-32768, aoi_prefix="test",
            merge_filename="merged.tif",
        )
        assert result is None

    def test_single_tile_clipped(self, tmp_path):
        t1 = str(tmp_path / "tile1.tif")
        _create_synthetic_tile(t1, -1.0, 2.0, -1.0, 2.0)

        fb = _Feedback()
        result = clip_and_merge_tiles(
            [t1], south=0.0, north=1.0, west=0.0, east=1.0,
            temp_dir=str(tmp_path), feedback=fb,
            nodata_value=-32768, aoi_prefix="test",
            merge_filename="merged.tif",
        )
        assert result is not None
