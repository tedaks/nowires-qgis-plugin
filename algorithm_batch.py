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
Batch P2P Analysis Algorithm.
Supports One-to-Many and Many-to-One modes. Results are ranked by link margin.
Portions adapted from tedaks/nowires (MIT). See NOTICE.md.
"""

import logging
from typing import Any
from qgis.core import QgsProcessingException
from .base_algorithm import NoWiresAlgorithm, install_constants
from .constants import DEGREE_PADDING
from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid
from .geo_bounds import shortest_longitude_bounds_for, validate_coordinates
from .radio import K_FACTOR_PRESETS, resolve_k_factor, validate_itm_input_ranges
from .antenna import antenna_preset_key
from .clutter import LandCoverGrid, clutter_override_value, ensure_clutter_grid_for_area
from .batch_params import BATCH_PARAM_CONSTANTS, add_batch_params
from .batch_outputs import (
    _feat_attr, compute_batch_links, rank_batch_results,
)
from .temp_manager import TempDirManager
from .batch_analysis_params import BatchAnalysisParams
from .batch_writer import write_batch_outputs

logger = logging.getLogger(__name__)


def _features_to_points(features, source_crs, transform_fn, default_height):
    points = []
    for feat in features:
        geom = feat.geometry()
        if geom is None or geom.isEmpty() or geom.isMultipart():
            if geom is not None and geom.isMultipart():
                logger.debug("Skipping multipart feature %s", feat.id())
            continue
        pt = transform_fn(geom.asPoint(), source_crs)
        pdef = {"id": feat.id(), "lat": pt.y(), "lon": pt.x(),
                "height": _feat_attr(feat, "height", default_height),
                "gain_db": _feat_attr(feat, "gain_db", None)}
        pk = _feat_attr(feat, "antenna_preset", None)
        az = _feat_attr(feat, "azimuth", None)
        if pk is not None:
            pdef["antenna_preset"] = str(pk)
        if az is not None:
            pdef["azimuth"] = az
        points.append(pdef)
    return points


def _extract_batch_radio_params(algorithm, parameters, context):
    p = parameters
    _pD = algorithm.parameterAsDouble
    _pE = algorithm.parameterAsEnum
    _pF = algorithm.parameterAsFile
    tx_h = _pD(p, algorithm.TX_HEIGHT, context)
    rx_h = _pD(p, algorithm.RX_HEIGHT, context)
    f_mhz = _pD(p, algorithm.FREQ_MHZ, context)
    polarization = _pE(p, algorithm.POLARIZATION, context)
    climate = _pE(p, algorithm.CLIMATE, context)
    time_pct = _pD(p, algorithm.TIME_PCT, context)
    location_pct = _pD(p, algorithm.LOCATION_PCT, context)
    situation_pct = _pD(p, algorithm.SITUATION_PCT, context)
    tx_power = _pD(p, algorithm.TX_POWER, context)
    tx_gain_d = _pD(p, algorithm.TX_GAIN, context)
    rx_gain_d = _pD(p, algorithm.RX_GAIN, context)
    cable_loss = _pD(p, algorithm.CABLE_LOSS, context)
    rx_sens = _pD(p, algorithm.RX_SENSITIVITY, context)
    tx_pk = antenna_preset_key(_pE(p, algorithm.TX_ANTENNA_PRESET, context))
    rx_pk = antenna_preset_key(_pE(p, algorithm.RX_ANTENNA_PRESET, context))
    tx_az = _pD(p, algorithm.TX_ANTENNA_AZ, context)
    rx_az = _pD(p, algorithm.RX_ANTENNA_AZ, context)
    pi = _pE(p, algorithm.K_FACTOR_PRESET, context)
    kf = resolve_k_factor(
        has_preset=pi < len(K_FACTOR_PRESETS), has_custom=True,
        custom_value=_pD(p, algorithm.K_FACTOR, context), preset_index=pi)
    n0 = _pD(p, algorithm.N0, context)
    epsilon = _pD(p, algorithm.EPSILON, context)
    sigma = _pD(p, algorithm.SIGMA, context)
    validate_itm_input_ranges(tx_height_m=tx_h, rx_height_m=rx_h, frequency_mhz=f_mhz,
        surface_refractivity_n0=n0, earth_conductivity_sigma=sigma)
    clutter_model_idx = _pE(p, algorithm.CLUTTER_MODEL, context)
    ce = clutter_model_idx > 0
    clutter_model = "advanced" if clutter_model_idx == 2 else "simple"
    cch_raw = _pD(p, algorithm.CCH_OVERRIDE, context)
    cch_override_m = cch_raw if cch_raw > 0.0 else None
    _crp = _pF(p, algorithm.CLUTTER_RASTER, context)
    cg = LandCoverGrid.from_raster(_crp) if _crp else None
    tco = clutter_override_value(_pE(p, algorithm.TX_CLUTTER_OVERRIDE, context))
    rco = clutter_override_value(_pE(p, algorithm.RX_CLUTTER_OVERRIDE, context))
    clutter_percentile = _pD(p, algorithm.CLUTTER_PERCENTILE, context)
    street_width_m = _pD(p, algorithm.STREET_WIDTH, context)
    bel_enabled = algorithm.parameterAsBool(parameters, algorithm.BEL_ENABLED, context)
    bel_building_type_idx = _pE(p, algorithm.BEL_BUILDING_TYPE, context)
    bel_building_type = ("traditional" if bel_building_type_idx == 0 else "thermally_efficient")
    bel_elevation_angle = _pD(p, algorithm.BEL_ELEVATION_ANGLE, context)
    tfb = _pD(p, algorithm.TX_FRONT_BACK_DB, context)
    rfb = _pD(p, algorithm.RX_FRONT_BACK_DB, context)
    return dict(tx_h=tx_h, rx_h=rx_h, f_mhz=f_mhz, polarization=polarization,
        climate=climate, time_pct=time_pct, location_pct=location_pct,
        situation_pct=situation_pct, tx_power=tx_power, tx_gain_d=tx_gain_d,
        rx_gain_d=rx_gain_d, cable_loss=cable_loss, rx_sens=rx_sens, tx_pk=tx_pk,
        rx_pk=rx_pk, tx_az=tx_az, rx_az=rx_az, kf=kf, n0=n0, epsilon=epsilon,
        sigma=sigma, ce=ce, cg=cg, tco=tco, rco=rco, tfb=tfb, rfb=rfb,
        clutter_model=clutter_model, cch_override_m=cch_override_m,
        clutter_percentile=clutter_percentile, street_width_m=street_width_m,
        bel_enabled=bel_enabled, bel_building_type=bel_building_type,
        bel_elevation_angle_deg=bel_elevation_angle)

def _collect_batch_inputs(algorithm, parameters, context, feedback):
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform
    mode = algorithm.parameterAsEnum(parameters, algorithm.MODE, context)
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    cache: dict[str, Any] = {}
    def _xform(point, src_crs):
        if src_crs is None or not src_crs.isValid() or src_crs.authid().upper() == "EPSG:4326":
            return point
        key = src_crs.authid() or src_crs.toWkt()
        t = cache.get(key) or QgsCoordinateTransform(src_crs, wgs84, context.transformContext())
        cache.setdefault(key, t)
        return t.transform(point)
    if mode == 0:
        tx_pt = algorithm.parameterAsPoint(parameters, algorithm.TX_POINT, context, crs=wgs84)
        if tx_pt is None:
            raise QgsProcessingException("TX point is required for One-to-Many mode.")
        candidate_tx = [{"lat": tx_pt.y(), "lon": tx_pt.x(), "height": None, "is_tx": True}]
        rx_src = algorithm.parameterAsSource(parameters, algorithm.RX_LAYER, context)
        if rx_src is None:
            raise QgsProcessingException("RX layer is required for One-to-Many mode.")
        rx_pts = list(rx_src.getFeatures())
        rx_points = _features_to_points(rx_pts, rx_src.sourceCrs(), _xform, 10.0)
        if not rx_points:
            raise QgsProcessingException("No valid RX points found.")
        feedback.pushInfo("One-to-Many: {} RX points".format(len(rx_points)))
        validate_coordinates(tx_pt.y(), tx_pt.x(), "TX")
        for pt in rx_points:
            validate_coordinates(pt["lat"], pt["lon"], "RX")
    else:
        tx_src = algorithm.parameterAsSource(parameters, algorithm.TX_LAYER, context)
        if tx_src is None:
            raise QgsProcessingException("TX layer is required for Many-to-One mode.")
        tx_feats = list(tx_src.getFeatures())
        candidate_tx = _features_to_points(tx_feats, tx_src.sourceCrs(), _xform, 30.0)
        for tx in candidate_tx:
            tx["is_tx"] = True
        if not candidate_tx:
            raise QgsProcessingException("No valid TX points found.")
        rx_pt = algorithm.parameterAsPoint(parameters, algorithm.RX_POINT, context, crs=wgs84)
        if rx_pt is None:
            raise QgsProcessingException("RX point is required for Many-to-One mode.")
        rx_points = [{"id": 0, "lat": rx_pt.y(), "lon": rx_pt.x(), "height": None, "is_tx": False}]
        validate_coordinates(rx_pt.y(), rx_pt.x(), "RX")
        for tx in candidate_tx:
            validate_coordinates(tx["lat"], tx["lon"], "TX")
        feedback.pushInfo("Many-to-One: {} TX sites".format(len(candidate_tx)))
    rp = _extract_batch_radio_params(algorithm, parameters, context)
    lats = [pt["lat"] for pt in candidate_tx] + [pt["lat"] for pt in rx_points]
    lons = [pt["lon"] for pt in candidate_tx] + [pt["lon"] for pt in rx_points]
    south, north = min(lats), max(lats)
    pad = max(DEGREE_PADDING, (north - south) * 0.1)
    west, east = shortest_longitude_bounds_for(lons, padding_deg=pad)
    if rp["cg"] is None and rp["ce"]:
        rp["cg"] = ensure_clutter_grid_for_area(south=south - pad, north=north + pad,
            west=west - pad, east=east + pad, feedback=feedback)
    feedback.pushInfo("Downloading DEM data...")
    feedback.setProgress(5)
    dem_path = ensure_dem_for_area(
        south - pad, north + pad, west - pad, east + pad, feedback=feedback)
    if dem_path is None:
        raise QgsProcessingException("Failed to obtain DEM data for the analysis area.")
    feedback.pushInfo("Building elevation grid...")
    feedback.setProgress(15)
    try:
        elev = ElevationGrid(dem_path)
    except Exception:
        if rp["cg"] is not None:
            rp["cg"].close()
        raise
    try:
        total = len(candidate_tx) * len(rx_points)
        return BatchAnalysisParams(
            mode=mode, candidate_tx=candidate_tx, rx_points=rx_points, elev=elev,
            total=total, tx_h=rp["tx_h"], rx_h=rp["rx_h"], f_mhz=rp["f_mhz"],
            polarization=rp["polarization"], climate=rp["climate"],
            time_pct=rp["time_pct"], location_pct=rp["location_pct"],
            situation_pct=rp["situation_pct"], tx_power=rp["tx_power"],
            tx_gain_default=rp["tx_gain_d"], rx_gain_default=rp["rx_gain_d"],
            cable_loss=rp["cable_loss"], rx_sens=rp["rx_sens"],
            tx_default_preset_key=rp["tx_pk"], rx_default_preset_key=rp["rx_pk"],
            tx_default_az=rp["tx_az"], rx_default_az=rp["rx_az"],
            tx_front_back_db=rp["tfb"], rx_front_back_db=rp["rfb"],
            k_factor=rp["kf"], n0=rp["n0"], epsilon=rp["epsilon"], sigma=rp["sigma"],
            clutter_enabled=rp["ce"], clutter_grid=rp["cg"],
            tx_clutter_override=rp["tco"], rx_clutter_override=rp["rco"],
            clutter_model=rp["clutter_model"], cch_override_m=rp["cch_override_m"],
            clutter_percentile=rp["clutter_percentile"],
            street_width_m=rp["street_width_m"],
            bel_enabled=rp["bel_enabled"],
            bel_building_type=rp["bel_building_type"],
            bel_elevation_angle_deg=rp["bel_elevation_angle_deg"])
    except Exception:
        elev.close()
        if rp["cg"] is not None:
            rp["cg"].close()
        raise


def _report_batch_results(feedback, results, mode):
    feedback.pushInfo("\n" + "=" * 50 + "\nBATCH P2P RESULTS\n" + "=" * 50)
    viable = sum(1 for r in results if r["status"] == "VIABLE")
    feedback.pushInfo("Total links computed: {}".format(len(results)))
    feedback.pushInfo("Viable links: {} / {}".format(viable, len(results)))
    feedback.pushInfo("Top 5 ranked results:")
    for i, r in enumerate(results[:5]):
        cl = r["tx_lat"] if mode == 1 else r["rx_lat"]
        co = r["tx_lon"] if mode == 1 else r["rx_lon"]
        feedback.pushInfo(
            "  {}. {} ({:.5f},{:.5f}): {:.2f}km margin={:.1f}dB {}".format(
                i + 1, "TX" if mode == 0 else "TXc",
                cl, co, r["dist_km"], r["margin_db"], r["status"]))
    feedback.pushInfo("=" * 50)


class BatchAnalysisAlgorithm(NoWiresAlgorithm):
    """Batch point-to-point link analysis."""

    def initAlgorithm(self, config):
        add_batch_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        tmp_mgr = TempDirManager()
        rank_by = self.parameterAsEnum(parameters, self.RANK_BY, context)
        inp = _collect_batch_inputs(self, parameters, context, feedback)
        feedback.pushInfo("Computing batch P2P links...")
        feedback.setProgress(20)
        try:
            results = compute_batch_links(inp, feedback)
            results = rank_batch_results(results, rank_by)
            _report_batch_results(feedback, results, inp.mode)
            feedback.setProgress(85)
            return write_batch_outputs(
                self, parameters, context, feedback,
                results, inp.mode, tmp_mgr)
        finally:
            if inp.elev is not None:
                inp.elev.close()
            if inp.clutter_grid is not None:
                inp.clutter_grid.close()
            tmp_mgr.cleanup()
            tmp_mgr.warn_persistent(feedback)

    def shortHelpString(self):
        return ("Batch P2P analysis: One-to-Many (single TX→multiple RX) or "
                "Many-to-One (multiple TX→single RX). Ranked by margin/loss/clearance.")

    def name(self):
        return "batch_p2p_analysis"

    def displayName(self):
        return self.tr("Batch P2P Analysis")

    def createInstance(self):
        return BatchAnalysisAlgorithm()


install_constants(BatchAnalysisAlgorithm, BATCH_PARAM_CONSTANTS)
