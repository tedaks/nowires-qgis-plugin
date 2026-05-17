# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
/***************************************************************************
 NoWires
                      A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                              -------------------
         begin                : 2026-04-22
         copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
         email                : tedaks@gmail.com
 ***************************************************************************/

 /***************************************************************************
  *                                                                         *
  *   This program is free software; you can redistribute it and/or modify  *
  *   it under the terms of the GNU General Public License as published by  *
  *   the Free Software Foundation; either version 3 of the License, or     *
  *   (at your option) any later version.                                   *
  *                                                                         *
  ***************************************************************************/


OGR output writers for P2P profile line and Fresnel zone layers.
"""

from osgeo import ogr

from .report_markers import ogr_driver_for_path, remove_existing_ogr_dataset
from .constants import FRESNEL_60PCT_FACTOR
from .radio import PROP_MODE_NAMES

__all__ = ["write_profile_line", "write_fresnel_zone"]


def _require_ogr_driver(path):
    """Return the OGR driver for *path*, raising on failure."""
    driver = ogr.GetDriverByName(ogr_driver_for_path(path))
    if driver is None:
        raise RuntimeError("No OGR driver found for output path: {}".format(path))
    return driver


def write_profile_line(path, srs, tx_lat, tx_lon, rx_lat, rx_lon, dist_m, result,
                       itm_loss_db=None):
    driver = _require_ogr_driver(path)
    remove_existing_ogr_dataset(driver, path)
    ds = None
    try:
        ds = driver.CreateDataSource(path)
        if ds is None:
            raise RuntimeError("Failed to create dataset at {}".format(path))
        layer = ds.CreateLayer("link", srs=srs, geom_type=ogr.wkbLineString)
        layer.CreateField(ogr.FieldDefn("distance", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("loss_db", ogr.OFTReal))
        layer.CreateField(ogr.FieldDefn("mode", ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn("mode_name", ogr.OFTString))

        feat = ogr.Feature(layer.GetLayerDefn())
        geom = ogr.Geometry(ogr.wkbLineString)
        geom.AddPoint(tx_lon, tx_lat)
        geom.AddPoint(rx_lon, rx_lat)
        feat.SetGeometry(geom)
        feat.SetField("distance", dist_m)
        feat.SetField("loss_db", itm_loss_db if itm_loss_db is not None else result.loss_db)
        feat.SetField("mode", result.mode)
        feat.SetField("mode_name", PROP_MODE_NAMES.get(result.mode, "Unknown"))
        layer.CreateFeature(feat)
    finally:
        ds = None


def write_fresnel_zone(
    poly_path, lines_path, srs, tx_lat, tx_lon, rx_lat, rx_lon,
    distances, terrain_bulge, los_h, fresnel_r, dist_m,
):
    poly_driver = _require_ogr_driver(poly_path)
    lines_driver = _require_ogr_driver(lines_path)
    remove_existing_ogr_dataset(poly_driver, poly_path)
    remove_existing_ogr_dataset(lines_driver, lines_path)
    n = len(distances)

    def _geo_points(heights):
        pts = []
        for i in range(n):
            t = distances[i] / dist_m if dist_m > 0 else 0
            lat = tx_lat + t * (rx_lat - tx_lat)
            dlon = rx_lon - tx_lon
            if dlon > 180:
                dlon -= 360
            elif dlon < -180:
                dlon += 360
            lon = ((tx_lon + t * dlon) + 180) % 360 - 180
            pts.append((float(lon), float(lat), float(heights[i])))
        return pts

    ds_poly = None
    try:
        ds_poly = poly_driver.CreateDataSource(poly_path)
        if ds_poly is None:
            raise RuntimeError("Failed to create dataset at {}".format(poly_path))
        layer_poly = ds_poly.CreateLayer(
            "fresnel_zones", srs=srs, geom_type=ogr.wkbPolygon
        )
        layer_poly.CreateField(ogr.FieldDefn("type", ogr.OFTString))
        layer_poly.CreateField(ogr.FieldDefn("blocked", ogr.OFTInteger))

        upper_pts = _geo_points(los_h + fresnel_r)
        lower_pts = _geo_points(los_h - fresnel_r)

        ring_f1 = ogr.Geometry(ogr.wkbLinearRing)
        for lon, lat, z in upper_pts:
            ring_f1.AddPoint(lon, lat, z)
        for lon, lat, z in reversed(lower_pts):
            ring_f1.AddPoint(lon, lat, z)
        ring_f1.AddPoint(upper_pts[0][0], upper_pts[0][1], upper_pts[0][2])

        poly_f1 = ogr.Geometry(ogr.wkbPolygon)
        poly_f1.AddGeometry(ring_f1)

        feat_f1 = ogr.Feature(layer_poly.GetLayerDefn())
        feat_f1.SetGeometry(poly_f1)
        feat_f1.SetField("type", "fresnel_zone")
        feat_f1.SetField("blocked", 0)
        layer_poly.CreateFeature(feat_f1)

        upper_band = _geo_points(los_h - FRESNEL_60PCT_FACTOR * fresnel_r)
        lower_band = _geo_points(los_h - fresnel_r)

        ring_band = ogr.Geometry(ogr.wkbLinearRing)
        for lon, lat, z in upper_band:
            ring_band.AddPoint(lon, lat, z)
        for lon, lat, z in reversed(lower_band):
            ring_band.AddPoint(lon, lat, z)
        ring_band.AddPoint(upper_band[0][0], upper_band[0][1], upper_band[0][2])

        poly_band = ogr.Geometry(ogr.wkbPolygon)
        poly_band.AddGeometry(ring_band)

        feat_band = ogr.Feature(layer_poly.GetLayerDefn())
        feat_band.SetGeometry(poly_band)
        feat_band.SetField("type", "fresnel_violation_band_60pct")
        feat_band.SetField("blocked", 0)
        layer_poly.CreateFeature(feat_band)
    finally:
        ds_poly = None

    ds_lines = None
    try:
        ds_lines = lines_driver.CreateDataSource(lines_path)
        if ds_lines is None:
            raise RuntimeError("Failed to create dataset at {}".format(lines_path))
        layer_lines = ds_lines.CreateLayer(
            "fresnel_lines", srs=srs, geom_type=ogr.wkbLineString
        )
        layer_lines.CreateField(ogr.FieldDefn("type", ogr.OFTString))
        layer_lines.CreateField(ogr.FieldDefn("blocked", ogr.OFTInteger))

        terrain_pts = _geo_points(terrain_bulge)
        terrain_line = ogr.Geometry(ogr.wkbLineString)
        for lon, lat, z in terrain_pts:
            terrain_line.AddPoint(lon, lat, z)

        feat_ter = ogr.Feature(layer_lines.GetLayerDefn())
        feat_ter.SetGeometry(terrain_line)
        feat_ter.SetField("type", "terrain")
        feat_ter.SetField("blocked", int(bool((terrain_bulge > los_h).any())))
        layer_lines.CreateFeature(feat_ter)

        los_pts = _geo_points(los_h)
        los_line = ogr.Geometry(ogr.wkbLineString)
        for lon, lat, z in los_pts:
            los_line.AddPoint(lon, lat, z)

        feat_los = ogr.Feature(layer_lines.GetLayerDefn())
        feat_los.SetGeometry(los_line)
        feat_los.SetField("type", "los")
        feat_los.SetField("blocked", 0)
        layer_lines.CreateFeature(feat_los)
    finally:
        ds_lines = None
    return poly_path, lines_path
