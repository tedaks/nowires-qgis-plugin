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
         copyright            : (C) 2026 Daniel Hulshof Saint Martin
                                 Adaptations (C) 2026 Bortre Tenamo
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


Contour Lines Generation Algorithm.

Generates contour lines and optional hillshade overlay from Copernicus
GLO-30 DEM data. Adapted from the ContourLines QGIS plugin by
Daniel Hulshof Saint Martin.

Portions of this module are adapted from the ContourLines QGIS plugin
and were originally distributed under the GPL. See NOTICE.md for
attribution details.
"""

import errno
import os
import shutil

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsProcessingException,
    QgsProcessingParameterAuthConfig,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterColor,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
    QgsProject,
    QgsVectorLayer,
)

from .base_algorithm import NoWiresAlgorithm
from .constants import MAX_AOI_EXTENT_DEGREES, METERS_PER_FOOT

from .contour_generation import generate_contour_lines, reproject_and_export
from .contour_pipeline import (
    setup_proxy_opener,
    write_aoi_shapefile,
    download_and_merge_tiles,
    load_dem_output,
    load_overlay_layer,
)
from .contour_smoothing import _raster_calc, smooth_contour_dem
from .contour_symbology import apply_contour_symbology
from .dem_downloader import get_temp_dir
from .processing_utils import queue_layer_for_loading
from .temp_manager import TempDirManager
from .three_d import configure_contours_for_3d



class ContourLinesAlgorithm(NoWiresAlgorithm):
    """Generate contour lines from Copernicus GLO-30 DEM."""

    GROUP_NAME = "Terrain Analysis"
    GROUP_ID = "terrain_analysis"

    AREA_OF_INTEREST = "AREA_OF_INTEREST"
    INTERVAL = "INTERVAL"
    UNIT = "UNIT"
    SMOOTHING = "SMOOTHING"
    COLOR = "COLOR"
    ELEVATION_MAP = "ELEVATION_MAP"
    PROXY_AUTH = "PROXY_AUTH"
    OUTPUT = "OUTPUT"
    OUTPUT_DEM = "OUTPUT_DEM"

    def __init__(self):
        super().__init__()
        self.temp_dir = get_temp_dir()  # persistent DEM cache dir (never cleaned)
        self.status_total = 0.0
        self.progress = 0.0
        self._raster_layer_ids = []
        self._tmp = TempDirManager()  # per-run temp manager for clip/reproj files
        self._contour_layer_id = None

    def initAlgorithm(self, config):
        self.addParameter(QgsProcessingParameterExtent(
            self.AREA_OF_INTEREST, "Area of Interest", optional=False))
        self.addParameter(QgsProcessingParameterEnum(
            name=self.UNIT, description=self.tr("Contour interval unit"),
            options=["Metres", "Feet"], defaultValue=0, optional=False))
        self.addParameter(QgsProcessingParameterNumber(
            name=self.INTERVAL, description=self.tr("Contour interval"),
            type=QgsProcessingParameterNumber.Type.Integer,
            defaultValue=10, minValue=1, maxValue=5000, optional=False))
        self.addParameter(QgsProcessingParameterEnum(
            name=self.SMOOTHING, description=self.tr("Contour line smoothing level"),
            options=["None", "Low", "Medium", "High"], defaultValue="Medium",
            usesStaticStrings=True, optional=False))
        color_param = QgsProcessingParameterColor(
            name=self.COLOR, description=self.tr("Contour line colour"),
            defaultValue="#cc7700cc", optional=False)
        color_param.setOpacityEnabled(True)
        self.addParameter(color_param)
        self.addParameter(QgsProcessingParameterBoolean(
            name=self.ELEVATION_MAP,
            description=self.tr("Generate Elevation Overlay (Hillshade)"),
            defaultValue=True, optional=False))
        self.addParameter(QgsProcessingParameterAuthConfig(
            name=self.PROXY_AUTH,
            description=self.tr("Proxy authentication (optional)"), optional=True))
        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT, "Contour lines output"))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUTPUT_DEM, "Raw DEM output (3D terrain)",
            "GeoTIFF files (*.tif)", optional=True))

    def _validate_aoi(self, parameters, context):
        aoi = self.parameterAsExtent(
            parameters, self.AREA_OF_INTEREST, context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"))
        if aoi.isNull() or not aoi.isFinite():
            raise QgsProcessingException(self.tr(
                "Invalid area of interest (NaN values detected).\n\n"
                "Please draw a rectangle directly using the extent tool."))
        geom = QgsGeometry.fromRect(aoi)
        if geom.isNull() or geom.isEmpty():
            raise QgsProcessingException(self.tr("Could not create the area of interest geometry."))
        w, h = aoi.width(), aoi.height()
        if w > MAX_AOI_EXTENT_DEGREES or h > MAX_AOI_EXTENT_DEGREES:
            raise QgsProcessingException(self.tr(
                "Area of interest is too large ({}° x {}°). Maximum is {}°.".format(
                    w, h, MAX_AOI_EXTENT_DEGREES)))
        return aoi, geom

    def processAlgorithm(self, parameters, context, feedback):
        self._raster_layer_ids = []
        self._contour_layer_id = None
        self.status_total = 0.0
        self.progress = 0.0
        self._tmp = TempDirManager()
        os.makedirs(self.temp_dir, exist_ok=True)
        feedback.pushInfo("\nTemporary folder: " + self.temp_dir)
        try:
            aoi, aoi_geom = self._validate_aoi(parameters, context)
            aoi_shp_path = os.path.join(self.temp_dir, "area_of_interest.shp")
            write_aoi_shapefile(aoi_geom, aoi_shp_path)

            interval = self.parameterAsInt(parameters, self.INTERVAL, context)
            use_feet = self.parameterAsEnum(parameters, self.UNIT, context) == 1
            smoothing = self.parameterAsString(parameters, self.SMOOTHING, context)
            color = self.parameterAsColor(parameters, self.COLOR, context)
            gen_overlay = self.parameterAsBool(parameters, self.ELEVATION_MAP, context)
            auth_id = self.parameterAsString(parameters, self.PROXY_AUTH, context)
            proxy_opener = setup_proxy_opener(auth_id, feedback)

            self.status_total = 100.0 / 7

            merged_path, clip_temps, gdal_callback, _ = download_and_merge_tiles(
                aoi.yMinimum(), aoi.yMaximum(), aoi.xMinimum(), aoi.xMaximum(),
                self.temp_dir, aoi_shp_path, proxy_opener,
                feedback, self.progress, self.status_total)
            if merged_path is None:
                feedback.reportError(
                    "DEM download/merge failed for the selected area.")
                return {}
            for _cf in clip_temps:
                self._tmp.add_file(_cf)
            self.progress += 2
            feedback.setProgress(int(self.progress * self.status_total))

            dem_output = self.parameterAsFileOutput(parameters, self.OUTPUT_DEM, context)
            elevation_dem_path = None
            if gen_overlay or dem_output:
                elevation_dem_path = os.path.join(self.temp_dir, "elevation_contour.tif")
                self._tmp.add_file(elevation_dem_path)
                shutil.copy2(merged_path, elevation_dem_path)

            smooth_contour_dem(
                smoothing, merged_path, self.temp_dir,
                feedback, self.progress, self.status_total,
                tmp_manager=self._tmp)
            if feedback.isCanceled():
                return {}
            self.progress += 1
            feedback.setProgress(int(self.progress * self.status_total))

            if use_feet:
                feedback.pushInfo("\nConverting elevation values from metres to feet")
                merged_metres = os.path.join(self.temp_dir, "merged_metres.tif")
                self._tmp.add_file(merged_metres)
                os.replace(merged_path, merged_metres)
                _raster_calc(lambda A: A * METERS_PER_FOOT,
                             output_path=merged_path, nodata=-32768,
                             overwrite=True, A=merged_metres)

            feedback.pushInfo("\nGenerating contour lines")
            contour_shp_path, tmp_shp_dir = generate_contour_lines(
                merged_path, interval, self.temp_dir, gdal_callback)
            if contour_shp_path is None:
                feedback.reportError("Contour generation produced no output.")
                return {}
            self._tmp.add_dir(tmp_shp_dir)
            if feedback.isCanceled():
                return {}
            self.progress += 1
            feedback.setProgress(int(self.progress * self.status_total))

            output_dest = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
            try:
                final_output_path, reproj_dir = reproject_and_export(
                    contour_shp_path, context.project().crs(), output_dest,
                    self.temp_dir)
            except OSError as exc:
                if exc.errno == errno.ENOSPC:
                    feedback.reportError(
                        "Disk full while writing contour output: {}".format(exc))
                else:
                    feedback.pushWarning(
                        "Could not write contour output: {}".format(exc))
                return {}
            if reproj_dir is not None:
                self._tmp.add_dir(reproj_dir)

            unit_label = "ft" if use_feet else "m"
            layer_name = "Contour Lines ({}{})".format(interval, unit_label)
            layer = QgsVectorLayer(final_output_path, layer_name)
            feedback.pushInfo("Contour lines generated: " + str(layer.featureCount()))

            apply_contour_symbology(layer, color, interval)
            configure_contours_for_3d(layer, elevation_field="ELEV")
            self.progress += 1
            feedback.setProgress(int(self.progress * self.status_total))

            if dem_output:
                lid = load_dem_output(dem_output, elevation_dem_path, context, feedback)
                if lid:
                    self._raster_layer_ids.append(lid)

            if gen_overlay:
                lid, overlay_dir = load_overlay_layer(
                    elevation_dem_path, self.temp_dir, context, feedback)
                if lid:
                    self._raster_layer_ids.append(lid)
                self._tmp.make_dir("overlay_persistent", persistent=True)

            queue_layer_for_loading(context, layer, layer_name)
            self._contour_layer_id = layer.id()
            feedback.pushInfo("\nDone.")
            return {self.OUTPUT: final_output_path, self.OUTPUT_DEM: dem_output}
        finally:
            self._tmp.cleanup()
            self._tmp.warn_persistent(feedback)

    def postProcessAlgorithm(self, context, feedback):
        """Persist layer tracking state after successful algorithm execution."""
        if self._contour_layer_id is not None:
            QgsProject.instance().writeEntry(
                "NoWires", "last_contour_layer_id", self._contour_layer_id)
        return super().postProcessAlgorithm(context, feedback)

    def name(self):
        return "contour_lines"

    def displayName(self):
        return self.tr("Contour Lines")

    def createInstance(self):
        return ContourLinesAlgorithm()
