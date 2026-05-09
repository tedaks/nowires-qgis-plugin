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


OGR marker-layer helpers for NoWires report outputs.
"""

from __future__ import annotations

import os
from pathlib import Path

from osgeo import ogr, osr


_OGR_DRIVER_BY_EXT = {
    ".shp": "ESRI Shapefile",
    ".gpkg": "GPKG",
    ".geojson": "GeoJSON",
    ".json": "GeoJSON",
    ".kml": "KML",
}


def ogr_driver_for_path(path):
    """Return the OGR driver name appropriate for ``path``'s extension.

    Defaults to GPKG when the extension is unknown — GPKG is the modern
    QGIS Processing default and tolerates the geometry types we write.
    """
    ext = os.path.splitext(str(path))[1].lower()
    return _OGR_DRIVER_BY_EXT.get(ext, "GPKG")


def remove_existing_ogr_dataset(driver, path):
    """Best-effort removal of an existing OGR dataset before recreating it.

    Older GDAL releases let ``driver.Open`` return None for missing paths;
    GDAL 3.10+ raises ``RuntimeError`` instead. Using ``os.path.exists`` is
    portable across both.
    """
    str_path = str(path)
    if os.path.exists(str_path):
        try:
            driver.DeleteDataSource(str_path)
        except RuntimeError:
            try:
                os.remove(str_path)
            except OSError:
                pass


def build_p2p_marker_records(
    tx_lat,
    tx_lon,
    rx_lat,
    rx_lon,
    tx_h,
    rx_h,
    tx_gain,
    rx_gain,
    tx_power_dbm,
    rx_sensitivity_dbm,
):
    """Return the TX/RX marker attribute rows."""
    return [
        {
            "role": "TX",
            "latitude": tx_lat,
            "longitude": tx_lon,
            "height_m": tx_h,
            "gain_dbi": tx_gain,
            "power_dbm": tx_power_dbm,
            "sensitivity_dbm": None,
        },
        {
            "role": "RX",
            "latitude": rx_lat,
            "longitude": rx_lon,
            "height_m": rx_h,
            "gain_dbi": rx_gain,
            "power_dbm": None,
            "sensitivity_dbm": rx_sensitivity_dbm,
        },
    ]


def write_p2p_marker_layer(
    path,
    tx_lat,
    tx_lon,
    rx_lat,
    rx_lon,
    tx_h,
    rx_h,
    tx_gain,
    rx_gain,
    tx_power_dbm,
    rx_sensitivity_dbm,
):
    """Write a TX/RX point layer to disk with OGR."""
    path = Path(path)
    driver = ogr.GetDriverByName(ogr_driver_for_path(path))
    remove_existing_ogr_dataset(driver, path)

    ds = driver.CreateDataSource(str(path))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    layer = ds.CreateLayer("markers", srs=srs, geom_type=ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("role", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("latitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("longitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("height_m", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("gain_dbi", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("power_dbm", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("sens_dbm", ogr.OFTReal))

    for row in build_p2p_marker_records(
        tx_lat=tx_lat,
        tx_lon=tx_lon,
        rx_lat=rx_lat,
        rx_lon=rx_lon,
        tx_h=tx_h,
        rx_h=rx_h,
        tx_gain=tx_gain,
        rx_gain=rx_gain,
        tx_power_dbm=tx_power_dbm,
        rx_sensitivity_dbm=rx_sensitivity_dbm,
    ):
        feature = ogr.Feature(layer.GetLayerDefn())
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.AddPoint(row["longitude"], row["latitude"])
        feature.SetGeometry(geometry)
        feature.SetField("role", row["role"])
        feature.SetField("latitude", row["latitude"])
        feature.SetField("longitude", row["longitude"])
        feature.SetField("height_m", row["height_m"])
        feature.SetField("gain_dbi", row["gain_dbi"])
        if row["power_dbm"] is not None:
            feature.SetField("power_dbm", row["power_dbm"])
        if row["sensitivity_dbm"] is not None:
            feature.SetField("sens_dbm", row["sensitivity_dbm"])
        layer.CreateFeature(feature)

    ds = None
    return str(path)