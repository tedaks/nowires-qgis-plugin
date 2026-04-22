# -*- coding: utf-8 -*-
"""
/***************************************************************************
  NoWires
                      A QGIS plugin
  Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                              -------------------
        begin                : 2026-04-22
        copyright            : (C) 2024 Bortre Tenamo
                               Adaptations (C) 2026 by Bortre Tenamo
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


Coverage Radius Sweep Algorithm.

Estimates maximum, minimum, and average coverage distances by sweeping
bearings from the transmitter location.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import math
import logging

logger = logging.getLogger(__name__)
import os
import tempfile

import numpy as np

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    Qgis,
    QgsGeometry,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterVectorDestination,
    QgsProject,
    QgsVectorLayer,
)
from osgeo import gdal, ogr, osr

from .dem_downloader import ensure_dem_for_area
from .elevation import ElevationGrid, haversine_m, bearing_destination
from .coverage_engine import compute_coverage_radius
from .radio import PROP_MODE_NAMES


class CoverageRadiusAlgorithm(QgsProcessingAlgorithm):
    """Coverage radius estimation per bearing."""

    TX_POINT = "TX_POINT"
    TX_HEIGHT = "TX_HEIGHT"
    RX_HEIGHT = "RX_HEIGHT"
    FREQ_MHZ = "FREQ_MHZ"
    SEARCH_RADIUS = "SEARCH_RADIUS"
    POLARIZATION = "POLARIZATION"
    CLIMATE = "CLIMATE"
    TX_POWER = "TX_POWER"
    TX_GAIN = "TX_GAIN"
    RX_GAIN = "RX_GAIN"
    CABLE_LOSS = "CABLE_LOSS"
    RX_SENSITIVITY = "RX_SENSITIVITY"
    ANTENNA_AZ = "ANTENNA_AZ"
    ANTENNA_BW = "ANTENNA_BW"
    N0 = "N0"
    EPSILON = "EPSILON"
    SIGMA = "SIGMA"
    OUTPUT = "OUTPUT"

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterPoint(self.TX_POINT, "Transmitter (TX) point")
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_HEIGHT,
                "TX antenna height (m)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=30.0,
                minValue=0.1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_HEIGHT,
                "RX antenna height (m)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=0.1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.FREQ_MHZ,
                "Frequency (MHz)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=300.0,
                minValue=1.0,
                maxValue=40000.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SEARCH_RADIUS,
                "Search radius (km)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=100.0,
                minValue=1.0,
                maxValue=500.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.POLARIZATION,
                "Polarization",
                options=["Horizontal", "Vertical"],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CLIMATE,
                "Climate zone",
                options=[
                    "Equatorial",
                    "Continental Subtropical",
                    "Maritime Subtropical",
                    "Desert",
                    "Continental Temperate",
                    "Maritime Temperate (land)",
                    "Maritime Temperate (sea)",
                ],
                defaultValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_POWER,
                "TX power (dBm)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=43.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TX_GAIN,
                "TX antenna gain (dBi)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=8.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_GAIN,
                "RX antenna gain (dBi)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=2.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CABLE_LOSS,
                "Cable loss (dB)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=2.0,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RX_SENSITIVITY,
                "RX sensitivity (dBm)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=-100.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ANTENNA_AZ,
                "Antenna azimuth (deg, blank=omni)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
                maxValue=360.0,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ANTENNA_BW,
                "Antenna beamwidth (deg)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=360.0,
                minValue=1.0,
                maxValue=360.0,
            )
        )
        p_n0 = QgsProcessingParameterNumber(
            self.N0,
            "Surface refractivity N0",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=301.0,
            minValue=0.0,
        )
        p_n0.setFlags(p_n0.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        self.addParameter(p_n0)

        p_eps = QgsProcessingParameterNumber(
            self.EPSILON,
            "Dielectric constant (epsilon)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=15.0,
            minValue=0.0,
        )
        p_eps.setFlags(p_eps.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        self.addParameter(p_eps)

        p_sig = QgsProcessingParameterNumber(
            self.SIGMA,
            "Conductivity (S/m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.005,
            minValue=0.0,
        )
        p_sig.setFlags(p_sig.flags() | QgsProcessingParameterNumber.FlagAdvanced)
        self.addParameter(p_sig)

        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT, "Coverage radius polygon"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem

        tx_point = self.parameterAsPoint(
            parameters,
            self.TX_POINT,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        if tx_point is None:
            raise ValueError("TX point is required.")

        tx_lat = tx_point.y()
        tx_lon = tx_point.x()

        tx_h = self.parameterAsDouble(parameters, self.TX_HEIGHT, context)
        rx_h = self.parameterAsDouble(parameters, self.RX_HEIGHT, context)
        f_mhz = self.parameterAsDouble(parameters, self.FREQ_MHZ, context)
        radius_km = self.parameterAsDouble(parameters, self.SEARCH_RADIUS, context)
        polarization = self.parameterAsEnum(parameters, self.POLARIZATION, context)
        climate = self.parameterAsEnum(parameters, self.CLIMATE, context)
        tx_power = self.parameterAsDouble(parameters, self.TX_POWER, context)
        tx_gain = self.parameterAsDouble(parameters, self.TX_GAIN, context)
        rx_gain = self.parameterAsDouble(parameters, self.RX_GAIN, context)
        cable_loss = self.parameterAsDouble(parameters, self.CABLE_LOSS, context)
        rx_sens = self.parameterAsDouble(parameters, self.RX_SENSITIVITY, context)
        antenna_bw = self.parameterAsDouble(parameters, self.ANTENNA_BW, context)
        # Azimuth handling: None means omni when either unset or beamwidth is 360
        antenna_az = None
        if antenna_bw < 360.0:
            # Directional antenna: honour the azimuth if set, default to 0° if blank
            antenna_az = self.parameterAsDouble(parameters, self.ANTENNA_AZ, context)
        n0 = self.parameterAsDouble(parameters, self.N0, context)
        epsilon = self.parameterAsDouble(parameters, self.EPSILON, context)
        sigma = self.parameterAsDouble(parameters, self.SIGMA, context)

        feedback.pushInfo(
            "TX: ({:.5f}, {:.5f}), F={:.1f} MHz, Search={:.1f} km".format(
                tx_lat, tx_lon, f_mhz, radius_km
            )
        )

        # DEM area
        pad = max(0.05, radius_km / 111.32 * 0.1)
        r_lat = radius_km / 111.32
        r_lon = radius_km / (111.32 * max(math.cos(math.radians(tx_lat)), 0.01))
        south = tx_lat - r_lat - pad
        north = tx_lat + r_lat + pad
        west = tx_lon - r_lon - pad
        east = tx_lon + r_lon + pad

        feedback.pushInfo("Downloading DEM data...")
        feedback.setProgress(5)
        dem_path = ensure_dem_for_area(south, north, west, east, feedback=feedback)
        if dem_path is None:
            raise RuntimeError("Failed to obtain DEM data.")

        feedback.pushInfo("Building elevation grid...")
        feedback.setProgress(20)
        elev = ElevationGrid(dem_path)

        feedback.pushInfo("Computing coverage radius (360 bearings)...")
        feedback.setProgress(30)

        results = compute_coverage_radius(
            elev_grid=elev,
            tx_lat=tx_lat,
            tx_lon=tx_lon,
            tx_h_m=tx_h,
            rx_h_m=rx_h,
            f_mhz=f_mhz,
            radius_km=radius_km,
            tx_power_dbm=tx_power,
            tx_gain_dbi=tx_gain,
            rx_gain_dbi=rx_gain,
            cable_loss_db=cable_loss,
            rx_sensitivity_dbm=rx_sens,
            antenna_az_deg=antenna_az,
            antenna_beamwidth_deg=antenna_bw,
            polarization=polarization,
            climate=climate,
            N0=n0,
            epsilon=epsilon,
            sigma=sigma,
            feedback=feedback,
        )

        feedback.setProgress(85)

        output_dest = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        temp_dir = tempfile.mkdtemp(prefix="nowires_radius_")
        temp_polygon_path = os.path.join(temp_dir, "coverage_radius.shp")
        lines_shp_path = os.path.join(temp_dir, "coverage_radius_lines.shp")

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        driver = ogr.GetDriverByName("ESRI Shapefile")

        # --- Polygon layer ---
        ds_poly = driver.CreateDataSource(temp_polygon_path)
        layer_poly = ds_poly.CreateLayer(
            "coverage_radius", srs=srs, geom_type=ogr.wkbPolygon
        )
        layer_poly.CreateField(ogr.FieldDefn("bearing", ogr.OFTReal))
        layer_poly.CreateField(ogr.FieldDefn("radius_km", ogr.OFTReal))

        # Build polygon ring only from bearings with coverage
        ring = ogr.Geometry(ogr.wkbLinearRing)
        has_coverage = False
        for bearing_deg, radius_m in results:
            if radius_m > 0:
                has_coverage = True
                lat_end, lon_end = bearing_destination(
                    tx_lat, tx_lon, bearing_deg, radius_m
                )
                ring.AddPoint(lon_end, lat_end)

        if has_coverage:
            ring.AddPoint(ring.GetX(0), ring.GetY(0))
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
        else:
            poly = ogr.Geometry(ogr.wkbPolygon)

        feat_poly = ogr.Feature(layer_poly.GetLayerDefn())
        feat_poly.SetGeometry(poly)
        radii_km = [r / 1000.0 for _, r in results if r > 0]
        if radii_km:
            feat_poly.SetField("bearing", 0)
            feat_poly.SetField("radius_km", float(np.mean(radii_km)))
        layer_poly.CreateFeature(feat_poly)
        ds_poly = None

        # --- Lines layer ---
        ds_lines = driver.CreateDataSource(lines_shp_path)
        layer_lines = ds_lines.CreateLayer(
            "coverage_radius_lines", srs=srs, geom_type=ogr.wkbLineString
        )
        layer_lines.CreateField(ogr.FieldDefn("bearing", ogr.OFTReal))
        layer_lines.CreateField(ogr.FieldDefn("radius_km", ogr.OFTReal))

        for bearing_deg, radius_m in results:
            if radius_m > 0:
                lat_end, lon_end = bearing_destination(
                    tx_lat, tx_lon, bearing_deg, radius_m
                )
                feat_line = ogr.Feature(layer_lines.GetLayerDefn())
                line = ogr.Geometry(ogr.wkbLineString)
                line.AddPoint(tx_lon, tx_lat)
                line.AddPoint(lon_end, lat_end)
                feat_line.SetGeometry(line)
                feat_line.SetField("bearing", bearing_deg)
                feat_line.SetField("radius_km", radius_m / 1000.0)
                layer_lines.CreateFeature(feat_line)
        ds_lines = None

        # Load polygon layer for immediate visual feedback
        if output_dest:
            gdal.VectorTranslate(output_dest, temp_polygon_path)
            final_output_path = output_dest
        else:
            final_output_path = temp_polygon_path

        radius_layer = QgsVectorLayer(
            final_output_path, "Coverage Radius ({:.0f} MHz)".format(f_mhz)
        )
        QgsProject.instance().addMapLayer(radius_layer)

        # Also load lines layer
        lines_layer = QgsVectorLayer(
            lines_shp_path, "Coverage Radius Lines ({:.0f} MHz)".format(f_mhz)
        )
        QgsProject.instance().addMapLayer(lines_layer)

        feedback.setProgress(100)

        # Report
        radii = [r for _, r in results]
        max_r = max(radii) / 1000.0 if radii else 0.0
        min_r = min(radii) / 1000.0 if radii else 0.0
        avg_r = float(np.mean(radii)) / 1000.0 if radii else 0.0

        feedback.pushInfo("")
        feedback.pushInfo("=" * 40)
        feedback.pushInfo("COVERAGE RADIUS RESULTS")
        feedback.pushInfo("=" * 40)
        feedback.pushInfo("Max radius:  {:.2f} km".format(max_r))
        feedback.pushInfo("Min radius:  {:.2f} km".format(min_r))
        feedback.pushInfo("Avg radius:  {:.2f} km".format(avg_r))
        feedback.pushInfo("=" * 40)

        return {self.OUTPUT: final_output_path}

    def name(self):
        return "coverage_radius"

    def displayName(self):
        return self.tr("Coverage Radius Sweep")

    def group(self):
        return self.tr("Radio Propagation")

    def groupId(self):
        return "radio_propagation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return CoverageRadiusAlgorithm()
