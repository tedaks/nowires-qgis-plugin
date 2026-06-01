# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for Fresnel zone longitude overflow across antimeridian.

Before the fix, lon = tx_lon + t * dlon could exceed +/-180 when the
path crosses the antimeridian, creating invalid WGS84 coordinates.
"""
import numpy as np

from p2p.outputs import write_fresnel_zone


def _make_srs():
    from osgeo import osr
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


def test_lon_wrapped_across_antimeridian(tmp_path):
    """Interpolated longitudes must stay within [-180, 180] when the
    path crosses the antimeridian."""
    srs = _make_srs()
    n = 20
    dist_m = 100000.0
    distances = np.linspace(0, dist_m, n)
    los_h = np.full(n, 100.0)
    fresnel_r = np.full(n, 10.0)
    terrain_bulge = np.full(n, 50.0)
    tx_lat, tx_lon = 0.0, 179.0
    rx_lat, rx_lon = 0.0, -170.0

    poly_path = str(tmp_path / "fresnel_poly.shp")
    lines_path = str(tmp_path / "fresnel_lines.shp")

    write_fresnel_zone(
        poly_path, lines_path, srs, tx_lat, tx_lon, rx_lat, rx_lon,
        distances, terrain_bulge, los_h, fresnel_r, dist_m)

    from osgeo import ogr
    ds = ogr.OpenShared(poly_path)
    layer = ds.GetLayer()
    for feat in layer:
        geom = feat.GetGeometryRef()
        env = geom.GetEnvelope()
        assert env[0] >= -180.0, f"min_x {env[0]} < -180"
        assert env[1] <= 180.0, f"max_x {env[1]} > 180"
    ds = None