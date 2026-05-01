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


Batch P2P computation and output helpers.
"""

import csv
import json
import logging
import math

import numpy as np

from osgeo import ogr, osr
from qgis.core import QgsProcessingException

try:
    from qgis.core import NULL as _QGIS_NULL
except ImportError:
    _QGIS_NULL = None

from .report_payloads import ogr_driver_for_path, _remove_existing_ogr_dataset
from .batch_params import BATCH_MODE_OPTIONS, RANK_BY_OPTIONS
from .elevation import ElevationGrid, bearing_deg, haversine_m
from .radio import (
    build_pfl,
    itm_p2p_loss,
)
from .antenna import (
    ANTENNA_PRESET_KEYS,
    antenna_config_from_values,
    antenna_gain_adjustment_db,
)
from .clutter import compute_terminal_clutter_losses

__all__ = [
    "_feat_attr",
    "compute_batch_links",
    "rank_batch_results",
    "write_batch_marker_layer",
    "write_batch_csv",
    "write_batch_json",
]

logger = logging.getLogger(__name__)


def compute_batch_links(
    candidate_tx, rx_points, elev, tx_h, rx_h, f_mhz, polarization,
    climate, time_pct, location_pct, situation_pct, n0, epsilon, sigma,
    tx_power, tx_gain_default, rx_gain_default, cable_loss, rx_sens,
    tx_default_preset_key, rx_default_preset_key,
    tx_default_az, rx_default_az, tx_front_back_db, rx_front_back_db,
    k_factor, clutter_enabled, clutter_grid, tx_clutter_override,
    rx_clutter_override, feedback, total,
):
    wavelength_m = 299792458.0 / (f_mhz * 1e6)
    results = []
    count = 0

    for tx_def in candidate_tx:
        tx_lat = tx_def["lat"]
        tx_lon = tx_def["lon"]
        tx_h_eff = tx_def["height"] if tx_def["height"] is not None else tx_h

        for rx_def in rx_points:
            if feedback.isCanceled():
                raise QgsProcessingException("Batch analysis cancelled by user.")
            rx_lat = rx_def["lat"]
            rx_lon = rx_def["lon"]
            rx_h_eff = rx_def["height"] if rx_def["height"] is not None else rx_h

            try:
                dist_m = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)
                if dist_m < 1.0:
                    count += 1
                    continue

                profile_points = elev.terrain_profile(tx_lat, tx_lon, rx_lat, rx_lon, step_m=30.0)
                if len(profile_points) < 2:
                    count += 1
                    continue
                distances = [p[0] for p in profile_points]
                elevations = [p[1] for p in profile_points]
                elevations = [0.0 if math.isnan(e) else e for e in elevations]
                step_m_val = dist_m / max(len(distances) - 1, 1)
                pfl = build_pfl(elevations, step_m_val)

                itm_result = itm_p2p_loss(
                    h_tx__meter=tx_h_eff,
                    h_rx__meter=rx_h_eff,
                    profile=pfl,
                    climate=climate,
                    N0=n0,
                    f__mhz=f_mhz,
                    polarization=polarization,
                    epsilon=epsilon,
                    sigma=sigma,
                    time_pct=time_pct,
                    location_pct=location_pct,
                    situation_pct=situation_pct,
                )

                clutter_losses = compute_terminal_clutter_losses(
                    tx_lat=tx_lat,
                    tx_lon=tx_lon,
                    rx_lat=rx_lat,
                    rx_lon=rx_lon,
                    frequency_mhz=f_mhz,
                    enabled=clutter_enabled,
                    land_cover_grid=clutter_grid,
                    tx_override=tx_clutter_override,
                    rx_override=rx_clutter_override,
                )

                total_loss_db = itm_result.loss_db + clutter_losses.total_loss_db

                tx_bearing = bearing_deg(tx_lat, tx_lon, rx_lat, rx_lon)
                rx_bearing = bearing_deg(rx_lat, rx_lon, tx_lat, tx_lon)
                vertical_angle = math.degrees(
                    math.atan2((elevations[-1] + rx_h_eff) - (elevations[0] + tx_h_eff), max(dist_m, 1.0))
                )

                tx_gain_eff = tx_def["gain_db"] if tx_def["gain_db"] is not None else tx_gain_default
                rx_gain_eff = rx_def["gain_db"] if rx_def["gain_db"] is not None else rx_gain_default

                tx_preset_key = tx_def.get("antenna_preset", tx_default_preset_key)
                if tx_preset_key not in ANTENNA_PRESET_KEYS:
                    tx_preset_key = tx_default_preset_key
                tx_preset_idx = ANTENNA_PRESET_KEYS.index(tx_preset_key)
                tx_ant_config = antenna_config_from_values(
                    preset=tx_preset_idx,
                    azimuth_deg=tx_def.get("azimuth", tx_default_az),
                    front_back_db=tx_front_back_db,
                )
                rx_preset_key = rx_def.get("antenna_preset", rx_default_preset_key)
                if rx_preset_key not in ANTENNA_PRESET_KEYS:
                    rx_preset_key = rx_default_preset_key
                rx_preset_idx = ANTENNA_PRESET_KEYS.index(rx_preset_key)
                rx_ant_config = antenna_config_from_values(
                    preset=rx_preset_idx,
                    azimuth_deg=rx_def.get("azimuth", rx_default_az),
                    front_back_db=rx_front_back_db,
                )

                tx_ant_adj = antenna_gain_adjustment_db(tx_bearing, vertical_angle, tx_ant_config)
                rx_ant_adj = antenna_gain_adjustment_db(rx_bearing, -vertical_angle, rx_ant_config)
                ant_gain_adj_total = tx_ant_adj + rx_ant_adj

                eirp_eff = tx_power + tx_gain_eff - cable_loss
                prx_dbm = eirp_eff + rx_gain_eff + ant_gain_adj_total - total_loss_db
                margin_db = prx_dbm - rx_sens

                fresnel_r_arr = []
                for i in range(len(distances)):
                    d1 = distances[i]
                    d2 = dist_m - d1
                    if d1 > 0 and d2 > 0:
                        fr = math.sqrt(wavelength_m * d1 * d2 / dist_m)
                        fresnel_r_arr.append(fr)
                    else:
                        fresnel_r_arr.append(0.0)

                fresnel_r_arr = np.array(fresnel_r_arr, dtype=np.float64)
                elev_arr = np.array(elevations, dtype=np.float64)
                dist_arr = np.array(distances, dtype=np.float64)

                tx_antenna_h = elevations[0] + tx_h_eff
                rx_antenna_h = elevations[-1] + rx_h_eff
                t = np.divide(dist_arr, dist_m, out=np.zeros_like(dist_arr), where=dist_m > 0)
                a_eff = k_factor * 6371000.0
                bulge = (dist_arr * (dist_m - dist_arr)) / (2.0 * a_eff)
                los_h = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)
                terrain_bulge = elev_arr + bulge
                fresnel_clearance = (los_h - fresnel_r_arr) - terrain_bulge
                clearance_pct = float(
                    np.sum(fresnel_clearance > 0) / max(len(fresnel_clearance), 1) * 100
                )

                results.append({
                    "tx_lat": tx_lat,
                    "tx_lon": tx_lon,
                    "rx_lat": rx_lat,
                    "rx_lon": rx_lon,
                    "dist_m": dist_m,
                    "dist_km": dist_m / 1000.0,
                    "itm_loss_db": itm_result.loss_db,
                    "total_loss_db": total_loss_db,
                    "prx_dbm": prx_dbm,
                    "margin_db": margin_db,
                    "clearance_pct": clearance_pct,
                    "status": "VIABLE" if margin_db >= 0 else "NOT VIABLE",
                    "tx_height": tx_h_eff,
                    "rx_height": rx_h_eff,
                })
            except Exception as exc:
                logger.warning("Skipping TX(%.5f,%.5f)→RX(%.5f,%.5f): %s", tx_lat, tx_lon, rx_lat, rx_lon, exc)
                count += 1
                continue

            count += 1
            if count % 100 == 0 or count == total:
                feedback.setProgress(20 + int(60 * count / max(total, 1)))

    return results


def rank_batch_results(results, rank_by):
    if rank_by == 0:
        results.sort(key=lambda r: (r["margin_db"], r["clearance_pct"]), reverse=True)
    elif rank_by == 1:
        results.sort(key=lambda r: (r["itm_loss_db"], r["margin_db"]))
    else:
        results.sort(key=lambda r: (r["clearance_pct"], r["margin_db"]), reverse=True)
    return results


def _feat_attr(feat, name, default):
    """Return feat.attribute(name) cast to the same type as default.

    If default is None, returns float for numeric values or str for strings.
    Returns default on NULL attribute, missing field, or cast failure.
    Logs a warning when coercion truncates a value or fails entirely.
    """
    val = feat.attribute(name)
    if val is None or val == _QGIS_NULL:
        return default
    if default is None:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return str(val)
        logger.debug("Attribute '%s': unexpected type %s, using default", name, type(val).__name__)
        return default
    try:
        if isinstance(default, float):
            return float(val)
        if isinstance(default, int):
            coerced = int(float(val))
            if float(val) != coerced and isinstance(val, float):
                logger.warning(
                    "Attribute '%s': value %s truncated to %d for int field",
                    name, val, coerced,
                )
            return coerced
        if isinstance(default, str):
            return str(val)
        return default
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Attribute '%s': cannot coerce value %r to %s (%s), using default %r",
            name, val, type(default).__name__, exc, default,
        )
        return default


def write_batch_marker_layer(path, results, feedback, mode):
    driver = ogr.GetDriverByName(ogr_driver_for_path(path))
    _remove_existing_ogr_dataset(driver, path)
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
        headers = ["Point ID", "rank", "tx_lat", "tx_lon", "rx_lat", "rx_lon",
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