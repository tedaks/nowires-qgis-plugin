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


Batch P2P Analysis Algorithm.

Supports two modes:
- One-to-Many: single TX point to multiple RX points from a vector layer
- Many-to-One: multiple candidate TX sites from a vector layer to single RX point

Results are ranked by link margin and exported with a marker layer.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import logging
import os
import tempfile

logger = logging.getLogger(__name__)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
)

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid
from .radio import (
    K_FACTOR_PRESETS,
    resolve_k_factor,
    validate_itm_input_ranges,
)
from .antenna import antenna_preset_key
from .clutter import (
    LandCoverGrid,
    clutter_override_value,
    ensure_clutter_grid_for_area,
)
from .processing_utils import queue_layer_for_loading
from .batch_params import (
    BATCH_PARAM_CONSTANTS,
    BATCH_MODE_OPTIONS,
    add_batch_params,
)
from .batch_outputs import (
    _feat_attr,
    compute_batch_links,
    rank_batch_results,
    write_batch_marker_layer,
    write_batch_csv,
    write_batch_json,
)


def _install_constants(cls, constants_dict):
    for key, value in constants_dict.items():
        setattr(cls, key, value)


class BatchAnalysisAlgorithm(QgsProcessingAlgorithm):
    """Batch point-to-point link analysis."""

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        add_batch_params(self)

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform

        mode = self.parameterAsEnum(parameters, self.MODE, context)
        rank_by = self.parameterAsEnum(parameters, self.RANK_BY, context)
        wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform_cache = {}

        def transform_point_to_wgs84(point, source_crs):
            if (
                source_crs is None
                or not source_crs.isValid()
                or source_crs.authid().upper() == "EPSG:4326"
            ):
                return point
            key = source_crs.authid() or source_crs.toWkt()
            transform = transform_cache.get(key)
            if transform is None:
                transform = QgsCoordinateTransform(
                    source_crs,
                    wgs84_crs,
                    context.transformContext(),
                )
                transform_cache[key] = transform
            return transform.transform(point)

        if mode == 0:
            tx_point = self.parameterAsPoint(
                parameters, self.TX_POINT, context, crs=wgs84_crs,
            )
            if tx_point is None:
                raise QgsProcessingException("TX point is required for One-to-Many mode.")
            tx_lat = tx_point.y()
            tx_lon = tx_point.x()

            rx_source = self.parameterAsFeatureSource(parameters, self.RX_LAYER, context)
            if rx_source is None:
                raise QgsProcessingException("RX layer is required for One-to-Many mode.")
            rx_source_crs = rx_source.sourceCrs()
            rx_features = list(rx_source.getFeatures())
            if not rx_features:
                raise QgsProcessingException("RX layer has no features.")

            rx_points = []
            for feat in rx_features:
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                if geom.isMultipart():
                    continue
                pt = transform_point_to_wgs84(geom.asPoint(), rx_source_crs)
                height = _feat_attr(feat, "height", 10.0)
                preset_key = _feat_attr(feat, "antenna_preset", None)
                az = _feat_attr(feat, "azimuth", None)
                gain = _feat_attr(feat, "gain_db", None)
                rx_def = {
                    "id": feat.id(),
                    "lat": pt.y(),
                    "lon": pt.x(),
                    "height": height,
                    "gain_db": gain,
                }
                if preset_key is not None:
                    rx_def["antenna_preset"] = str(preset_key)
                if az is not None:
                    rx_def["azimuth"] = az
                rx_points.append(rx_def)
            if not rx_points:
                raise QgsProcessingException("No valid RX points found.")
            feedback.pushInfo(
                "One-to-Many: {} RX points from layer".format(len(rx_points))
            )

            candidate_tx = [{"lat": tx_lat, "lon": tx_lon, "height": None, "is_tx": True}]

        else:
            tx_source = self.parameterAsFeatureSource(parameters, self.TX_LAYER, context)
            if tx_source is None:
                raise QgsProcessingException("TX layer is required for Many-to-One mode.")
            tx_source_crs = tx_source.sourceCrs()
            tx_features = list(tx_source.getFeatures())
            if not tx_features:
                raise QgsProcessingException("TX layer has no features.")

            candidate_tx = []
            for feat in tx_features:
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                if geom.isMultipart():
                    continue
                pt = transform_point_to_wgs84(geom.asPoint(), tx_source_crs)
                height = _feat_attr(feat, "height", 30.0)
                preset_key = _feat_attr(feat, "antenna_preset", None)
                az = _feat_attr(feat, "azimuth", None)
                gain = _feat_attr(feat, "gain_db", None)
                tx_def = {
                    "id": feat.id(),
                    "lat": pt.y(),
                    "lon": pt.x(),
                    "height": height,
                    "gain_db": gain,
                    "is_tx": True,
                }
                if preset_key is not None:
                    tx_def["antenna_preset"] = str(preset_key)
                if az is not None:
                    tx_def["azimuth"] = az
                candidate_tx.append(tx_def)
            if not candidate_tx:
                raise QgsProcessingException("No valid TX points found.")

            rx_point = self.parameterAsPoint(
                parameters, self.RX_POINT, context, crs=wgs84_crs,
            )
            if rx_point is None:
                raise QgsProcessingException("RX point is required for Many-to-One mode.")
            rx_lat = rx_point.y()
            rx_lon = rx_point.x()
            rx_points = [{"id": 0, "lat": rx_lat, "lon": rx_lon, "height": None, "is_tx": False}]
            feedback.pushInfo(
                "Many-to-One: {} candidate TX sites".format(len(candidate_tx))
            )

        tx_h = self.parameterAsDouble(parameters, self.TX_HEIGHT, context)
        rx_h = self.parameterAsDouble(parameters, self.RX_HEIGHT, context)
        f_mhz = self.parameterAsDouble(parameters, self.FREQ_MHZ, context)
        polarization = self.parameterAsEnum(parameters, self.POLARIZATION, context)
        climate = self.parameterAsEnum(parameters, self.CLIMATE, context)
        time_pct = self.parameterAsDouble(parameters, self.TIME_PCT, context)
        location_pct = self.parameterAsDouble(parameters, self.LOCATION_PCT, context)
        situation_pct = self.parameterAsDouble(parameters, self.SITUATION_PCT, context)
        tx_power = self.parameterAsDouble(parameters, self.TX_POWER, context)
        tx_gain_default = self.parameterAsDouble(parameters, self.TX_GAIN, context)
        rx_gain_default = self.parameterAsDouble(parameters, self.RX_GAIN, context)
        cable_loss = self.parameterAsDouble(parameters, self.CABLE_LOSS, context)
        rx_sens = self.parameterAsDouble(parameters, self.RX_SENSITIVITY, context)
        tx_default_preset_key = antenna_preset_key(
            self.parameterAsEnum(parameters, self.TX_ANTENNA_PRESET, context)
        )
        rx_default_preset_key = antenna_preset_key(
            self.parameterAsEnum(parameters, self.RX_ANTENNA_PRESET, context)
        )
        tx_default_az = self.parameterAsDouble(parameters, self.TX_ANTENNA_AZ, context)
        rx_default_az = self.parameterAsDouble(parameters, self.RX_ANTENNA_AZ, context)
        preset_index = self.parameterAsEnum(parameters, self.K_FACTOR_PRESET, context)
        custom_k_factor = self.parameterAsDouble(parameters, self.K_FACTOR, context)
        k_factor = resolve_k_factor(
            has_preset=preset_index < len(K_FACTOR_PRESETS),
            has_custom=True,
            custom_value=custom_k_factor,
            preset_index=preset_index,
        )
        n0 = self.parameterAsDouble(parameters, self.N0, context)
        epsilon = self.parameterAsDouble(parameters, self.EPSILON, context)
        sigma = self.parameterAsDouble(parameters, self.SIGMA, context)

        validate_itm_input_ranges(
            tx_height_m=tx_h, rx_height_m=rx_h,
            frequency_mhz=f_mhz, surface_refractivity_n0=n0,
            earth_conductivity_sigma=sigma,
        )
        clutter_enabled = self.parameterAsEnum(parameters, self.CLUTTER_MODEL, context) == 1
        clutter_raster_path = self.parameterAsFile(parameters, self.CLUTTER_RASTER, context)
        if clutter_raster_path:
            clutter_grid = LandCoverGrid.from_raster(clutter_raster_path)
        else:
            clutter_grid = None
        tx_clutter_override = clutter_override_value(
            self.parameterAsEnum(parameters, self.TX_CLUTTER_OVERRIDE, context)
        )
        rx_clutter_override = clutter_override_value(
            self.parameterAsEnum(parameters, self.RX_CLUTTER_OVERRIDE, context)
        )

        all_lats = [p["lat"] for p in candidate_tx] + [p["lat"] for p in rx_points]
        all_lons = [p["lon"] for p in candidate_tx] + [p["lon"] for p in rx_points]
        south = min(all_lats)
        north = max(all_lats)
        west = min(all_lons)
        east = max(all_lons)
        pad = max(0.05, (north - south) * 0.1)

        if clutter_grid is None and clutter_enabled:
            clutter_grid = ensure_clutter_grid_for_area(
                south=south - pad, north=north + pad,
                west=west - pad, east=east + pad,
                feedback=feedback,
            )

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(
            south - pad, north + pad, west - pad, east + pad, feedback=feedback
        )
        if dem_path is None:
            raise QgsProcessingException("Failed to obtain DEM data for the analysis area.")
        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(15)
        elev = ElevationGrid(dem_path)

        feedback.pushInfo("Computing batch P2P links...")
        feedback.setProgress(20)

        tx_front_back_db = self.parameterAsDouble(parameters, self.TX_FRONT_BACK_DB, context)
        rx_front_back_db = self.parameterAsDouble(parameters, self.RX_FRONT_BACK_DB, context)
        total = len(candidate_tx) * len(rx_points)

        results = compute_batch_links(
            candidate_tx, rx_points, elev, tx_h, rx_h, f_mhz, polarization,
            climate, time_pct, location_pct, situation_pct, n0, epsilon, sigma,
            tx_power, tx_gain_default, rx_gain_default, cable_loss, rx_sens,
            tx_default_preset_key, rx_default_preset_key,
            tx_default_az, rx_default_az, tx_front_back_db, rx_front_back_db,
            k_factor, clutter_enabled, clutter_grid, tx_clutter_override,
            rx_clutter_override, feedback, total,
        )

        results = rank_batch_results(results, rank_by)

        feedback.pushInfo("")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo("BATCH P2P RESULTS")
        feedback.pushInfo("=" * 50)
        feedback.pushInfo("Total links computed: {}".format(len(results)))
        viable = sum(1 for r in results if r["status"] == "VIABLE")
        feedback.pushInfo("Viable links: {} / {}".format(viable, len(results)))
        feedback.pushInfo("Top 5 ranked results:")
        for i, r in enumerate(results[:5]):
            coord_lat = r["tx_lat"] if mode == 1 else r["rx_lat"]
            coord_lon = r["tx_lon"] if mode == 1 else r["rx_lon"]
            feedback.pushInfo(
                "  {}. {} → ({:.5f}, {:.5f}): {:.2f} km, margin={:.1f} dB, {}".format(
                    i + 1,
                    "TX" if mode == 0 else "TX candidate",
                    coord_lat, coord_lon,
                    r["dist_km"], r["margin_db"], r["status"],
                )
            )
        feedback.pushInfo("=" * 50)
        feedback.setProgress(85)

        _batch_tmp = None
        try:
            markers_dest = self.parameterAsFileOutput(parameters, self.OUTPUT_MARKERS, context)
            if markers_dest:
                markers_path = markers_dest
            else:
                _batch_tmp = tempfile.mkdtemp(prefix="nowires_batch_")
                markers_path = os.path.join(_batch_tmp, "batch_markers.gpkg")
                feedback.pushInfo(
                    "Temporary outputs are intentionally left on disk for QGIS layer loading: {}".format(_batch_tmp))
            write_batch_marker_layer(markers_path, results, feedback, mode)

            from qgis.core import QgsVectorLayer
            marker_layer = QgsVectorLayer(markers_path, "Batch P2P Markers")
            queue_layer_for_loading(context, marker_layer, "Batch P2P Markers")

            csv_path = self.parameterAsFileOutput(parameters, self.OUTPUT_CSV, context)
            json_path = self.parameterAsFileOutput(parameters, self.OUTPUT_JSON, context)

            if csv_path:
                write_batch_csv(csv_path, results, mode)
            if json_path:
                write_batch_json(json_path, results, mode)

            feedback.setProgress(100)

            output = {}
            if markers_path:
                output[self.OUTPUT_MARKERS] = markers_path
            if csv_path:
                output[self.OUTPUT_CSV] = csv_path
            if json_path:
                output[self.OUTPUT_JSON] = json_path

            return output
        finally:
            if _batch_tmp is not None:
                pass

    def shortHelpString(self):
        return (
            "Batch point-to-point link analysis supporting two modes:\n"
            "- One-to-Many: single TX to multiple RX points from a vector layer\n"
            "- Many-to-One: multiple candidate TX sites to a single RX point\n"
            "Results are ranked by link margin, path loss, or Fresnel clearance."
        )

    def name(self):
        return "batch_p2p_analysis"

    def displayName(self):
        return self.tr("Batch P2P Analysis")

    def group(self):
        return self.tr("Radio Propagation")

    def groupId(self):
        return "radio_propagation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return BatchAnalysisAlgorithm()


_install_constants(BatchAnalysisAlgorithm, BATCH_PARAM_CONSTANTS)