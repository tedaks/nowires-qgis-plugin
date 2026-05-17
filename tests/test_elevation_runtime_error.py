# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for assert→RuntimeError in ElevationGrid (v1.5.7 fix #2).

Before v1.5.7, ElevationGrid.sample, sample_line, and sample_grid used
``assert self.data is not None``, which is a no-op under ``python -O``.
A silent NaN read after close() would be much harder to diagnose than an
explicit RuntimeError.
"""

import numpy as np
import pytest


def _make_grid(tmp_path):
    from osgeo import gdal

    path = str(tmp_path / "test_dem.tif")
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, 4, 4, 1, gdal.GDT_Float32)
    srs = gdal.osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform([10.0, 0.01, 0, 45.0, 0, -0.01])
    band = ds.GetRasterBand(1)
    band.WriteArray(np.ones((4, 4), dtype=np.float32))
    band.FlushCache()
    ds = None
    return path


class TestSampleRaisesRuntimeErrorAfterClose:
    def test_sample_raises_runtime_error(self, tmp_path):
        from NoWires.elevation import ElevationGrid

        eg = ElevationGrid(_make_grid(tmp_path))
        result = eg.sample(44.99, 10.01)
        assert not np.isnan(result), "sample should return a real value"
        eg.close()
        with pytest.raises(RuntimeError, match="ElevationGrid closed"):
            eg.sample(44.99, 10.01)

    def test_sample_line_raises_runtime_error(self, tmp_path):
        from NoWires.elevation import ElevationGrid

        eg = ElevationGrid(_make_grid(tmp_path))
        result = eg.sample_line(44.99, 10.01, 44.97, 10.03, 5)
        assert len(result) == 5
        eg.close()
        with pytest.raises(RuntimeError, match="ElevationGrid closed"):
            eg.sample_line(44.99, 10.01, 44.97, 10.03, 5)

    def test_sample_grid_raises_runtime_error(self, tmp_path):
        from NoWires.elevation import ElevationGrid

        eg = ElevationGrid(_make_grid(tmp_path))
        result = eg.sample_grid(
            np.array([44.99, 44.98]), np.array([10.01, 10.02])
        )
        assert result.shape == (2, 2)
        eg.close()
        with pytest.raises(RuntimeError, match="ElevationGrid closed"):
            eg.sample_grid(
                np.array([44.99, 44.98]), np.array([10.01, 10.02])
            )