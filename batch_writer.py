# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
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


Batch P2P writer functions for marker layers, CSV, and JSON output.
"""

import csv
import json

from osgeo import ogr, osr

from .report_markers import ogr_driver_for_path, remove_existing_ogr_dataset
from .batch_params import BATCH_MODE_OPTIONS


def write_batch_marker_layer(path, results, feedback, mode):
    driver = ogr.GetDriverByName(ogr_driver_for_path(path))
    remove_existing_ogr_dataset(driver, path)
    ds = driver.CreateDataSource(str(path))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    layer = ds.CreateLayer("batch_markers", srs=srs, geom_type=ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("rank", ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn("point_id", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("margin_db", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("loss_db", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("itm_loss_db", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("dist_km", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("clearance_pct", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("status", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("tx_lat", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("tx_lon", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("rx_lat", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("rx_lon", ogr.OFTReal))

    for rank, r in enumerate(results, 1):
        feat = ogr.Feature(layer.GetLayerDefn())
        if mode == 1:
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.AddPoint(r["tx_lon"], r["tx_lat"])
            point_id = "TX({}, {:.5f}, {:.5f})".format(rank, r["tx_lat"], r["tx_lon"])
        else:
            geom = ogr.Geometry(ogr.wkbPoint)
            geom.AddPoint(r["rx_lon"], r["rx_lat"])
            point_id = "RX({}, {:.5f}, {:.5f})".format(rank, r["rx_lat"], r["rx_lon"])
        feat.SetGeometry(geom)
        feat.SetField("rank", rank)
        feat.SetField("point_id", point_id)
        feat.SetField("margin_db", r["margin_db"])
        feat.SetField("loss_db", r["total_loss_db"])
        feat.SetField("itm_loss_db", r["itm_loss_db"])
        feat.SetField("dist_km", round(r["dist_km"], 3))
        feat.SetField("clearance_pct", round(r["clearance_pct"], 1))
        feat.SetField("status", r["status"])
        feat.SetField("tx_lat", r["tx_lat"])
        feat.SetField("tx_lon", r["tx_lon"])
        feat.SetField("rx_lat", r["rx_lat"])
        feat.SetField("rx_lon", r["rx_lon"])
        layer.CreateFeature(feat)
        feat = None

    ds = None
    feedback.pushInfo("Wrote ranked marker layer to: {}".format(path))


def write_batch_csv(path, results, mode):
    with open(str(path), "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        headers = ["Point Id", "rank", "tx_lat", "tx_lon", "rx_lat", "rx_lon",
                   "dist_km", "itm_loss_db", "total_loss_db",
                   "margin_db", "clearance_pct", "status"]
        writer.writerow(headers)
        for rank, r in enumerate(results, 1):
            if mode == 1:
                point_id = "TX({}, {:.5f}, {:.5f})".format(rank, r["tx_lat"], r["tx_lon"])
            else:
                point_id = "RX({}, {:.5f}, {:.5f})".format(rank, r["rx_lat"], r["rx_lon"])
            writer.writerow([
                point_id,
                rank,
                r["tx_lat"],
                r["tx_lon"],
                r["rx_lat"],
                r["rx_lon"],
                round(r["dist_km"], 3),
                round(r["itm_loss_db"], 2),
                round(r["total_loss_db"], 2),
                round(r["margin_db"], 2),
                round(r["clearance_pct"], 1),
                r["status"],
            ])


def write_batch_json(path, results, mode):
    payload = {
        "report_type": "batch_p2p",
        "generated_by": "NoWires",
        "mode": BATCH_MODE_OPTIONS[mode],
        "total_links": len(results),
        "viable_links": sum(1 for r in results if r["status"] == "VIABLE"),
        "results": [
            {
                "rank": rank,
                "tx_lat": r["tx_lat"],
                "tx_lon": r["tx_lon"],
                "rx_lat": r["rx_lat"],
                "rx_lon": r["rx_lon"],
                "distance_km": round(r["dist_km"], 3),
                "itm_loss_db": round(r["itm_loss_db"], 2),
                "total_loss_db": round(r["total_loss_db"], 2),
                "margin_db": round(r["margin_db"], 2),
                "clearance_pct": round(r["clearance_pct"], 1),
                "status": r["status"],
            }
            for rank, r in enumerate(results, 1)
        ],
    }
    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")