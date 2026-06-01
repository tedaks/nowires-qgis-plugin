# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for ElevationGrid zero-division guard (v1.5.7 fix #16).

Source-level contract test: ElevationGrid.__init__ must check for zero
n_rows or n_cols and raise RuntimeError before the division. Creating a
0x0 GeoTIFF is not well-supported by GDAL, so we verify the guard exists
in the source code directly.
"""

import os
import pytest
import numpy as np


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "elevation.py"))


@pytest.mark.gdal_integration
def test_elevation_grid_source_has_zero_rows_cols_guard():
    """ElevationGrid.__init__ must guard against zero n_rows/n_cols."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "n_rows == 0" in source or "n_cols == 0" in source, (
        "ElevationGrid.__init__ must check for zero n_rows or n_cols before division"
    )
    assert "zero rows/cols" in source.lower() or "zero rows" in source.lower(), (
        "RuntimeError message should mention zero rows/cols"
    )


@pytest.mark.gdal_integration
def test_elevation_grid_guard_before_division():
    """The zero check must appear before the d_lat/d_lon computation."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    guard_pos = source.find("n_rows == 0")
    div_pos = source.find("self.d_lat")
    assert guard_pos != -1, "Zero-rows/cols guard not found"
    assert div_pos != -1, "d_lat division not found"
    assert guard_pos < div_pos, (
        f"Zero check at pos {guard_pos} must come before division at pos {div_pos}"
    )


@pytest.mark.gdal_integration
def test_elevation_grid_normal_dem_works(tmp_path):
    """ElevationGrid with a valid DEM must not raise."""
    from osgeo import gdal
    from NoWires.elevation import ElevationGrid

    path = str(tmp_path / "normal.tif")
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
    eg = ElevationGrid(path)
    assert eg.n_rows == 4
    assert eg.n_cols == 4
    eg.close()