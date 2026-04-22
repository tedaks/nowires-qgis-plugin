# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Daniel Hulshof Saint Martin
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


Contour Lines Generation Algorithm.

Generates contour lines and optional hillshade overlay from Copernicus
GLO-30 DEM data. Adapted from the ContourLines QGIS plugin by
Daniel Hulshof Saint Martin.

Portions of this module are adapted from the ContourLines QGIS plugin
and were originally distributed under the GPL. See NOTICE.md for
attribution details.
"""

import math
import os
import logging

logger = logging.getLogger(__name__)
import shutil
import tempfile

import numpy as np
from osgeo import gdal, ogr, osr

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsProcessingAlgorithm,
    QgsProcessingParameterAuthConfig,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterColor,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
    QgsProject,
    QgsRasterLayer,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsSymbolLayerReference,
    QgsTextFormat,
    QgsTextMaskSettings,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from .dem_downloader import (
    COPERNICUS_BASE_URL,
    get_temp_dir,
    required_tiles,
    download_tiles,
)
from .overlay_raster import build_overview_levels, choose_overlay_dimensions
from .qt_compat import painter_blend_mode_color_dodge


def _raster_calc(calc_func, output_path, nodata=-32768, overwrite=False, **inputs):
    arrays = {}
    datasets = []
    geo_transform = None
    projection = None
    rows = cols = 0
    for name, path in inputs.items():
        ds = gdal.Open(path)
        if ds is None:
            raise RuntimeError("Cannot open raster: " + str(path))
        datasets.append(ds)
        band = ds.GetRasterBand(1)
        if geo_transform is None:
            geo_transform = ds.GetGeoTransform()
            projection = ds.GetProjection()
            rows = ds.RasterYSize
            cols = ds.RasterXSize
        arr = band.ReadAsArray().astype(np.float32)
        input_nodata = band.GetNoDataValue()
        if input_nodata is not None:
            arr[arr == input_nodata] = np.nan
        arrays[name] = arr
    result = calc_func(**arrays)
    result[np.isnan(result)] = nodata
    if not overwrite and os.path.exists(output_path):
        raise RuntimeError("Output file already exists: " + output_path)
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)
    out_ds.SetGeoTransform(geo_transform)
    out_ds.SetProjection(projection)
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(nodata)
    out_band.WriteArray(result)
    out_band.FlushCache()
    out_ds = None
    for ds in datasets:
        ds = None


def _gaussian_kernel_2d(size, sigma=None):
    """Generate a normalised 2D Gaussian kernel as a flat string of coefficients.

    The kernel is centred at the middle pixel. If *sigma* is ``None`` it
    defaults to ``size / 6.0`` so that the kernel covers ±3σ (the standard
    "3-sigma rule" for a Gaussian), matching the visual appearance of the
    original hand-tuned kernels.

    Returns a space-separated string with exactly ``size * size`` coefficients,
    suitable for embedding in a GDAL VRT ``<Coefs>`` element.
    """
    if sigma is None:
        sigma = size / 6.0
    centre = size // 2
    coeffs = []
    for y in range(size):
        for x in range(size):
            dx = x - centre
            dy = y - centre
            val = math.exp(-(dx * dx + dy * dy) / (2.0 * sigma * sigma))
            coeffs.append(val)
    total = sum(coeffs)
    return " ".join("{:.6f}".format(c / total) for c in coeffs)


def _make_blur_vrt(vrt_path, src_path, kernel_size, sigma=None):
    """Build a VRT that applies a Gaussian blur of *kernel_size* × *kernel_size*.

    Creates the VRT from the source raster, then patches it to use GDAL's
    ``KernelFilteredSource`` with the generated Gaussian coefficients.
    """
    gdal.BuildVRT(vrt_path, src_path)
    with open(vrt_path, "rt") as f:
        data = f.read()
    data = data.replace("ComplexSource", "KernelFilteredSource")
    coefs = _gaussian_kernel_2d(kernel_size, sigma)
    data = data.replace(
        "<NODATA>-32768</NODATA>",
        '<NODATA>-32768</NODATA>'
        '<Kernel normalized="1"><Size>{size}</Size>'
        "<Coefs>{coefs}</Coefs></Kernel>".format(size=kernel_size, coefs=coefs),
    )
    with open(vrt_path, "wt") as f:
        f.write(data)


class ContourLinesAlgorithm(QgsProcessingAlgorithm):
    """Generate contour lines from Copernicus GLO-30 DEM."""

    AREA_OF_INTEREST = "AREA_OF_INTEREST"
    INTERVAL = "INTERVAL"
    UNIT = "UNIT"
    SMOOTHING = "SMOOTHING"
    COLOR = "COLOR"
    ELEVATION_MAP = "ELEVATION_MAP"
    PROXY_AUTH = "PROXY_AUTH"
    OUTPUT = "OUTPUT"

    def __init__(self):
        super().__init__()
        self.temp_dir = get_temp_dir()
        self.status_total = 0.0
        self.progress = 0.0

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterExtent(
                self.AREA_OF_INTEREST, "Area of Interest", optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.UNIT,
                description=self.tr("Contour interval unit"),
                options=["Metres", "Feet"],
                defaultValue=0,
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.INTERVAL,
                description=self.tr("Contour interval"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=10,
                minValue=1,
                maxValue=5000,
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.SMOOTHING,
                description=self.tr("Contour line smoothing level"),
                options=["None", "Low", "Medium", "High"],
                defaultValue="Medium",
                usesStaticStrings=True,
                optional=False,
            )
        )
        color_param = QgsProcessingParameterColor(
            name=self.COLOR,
            description=self.tr("Contour line colour"),
            defaultValue="#cc7700cc",
            optional=False,
        )
        color_param.setOpacityEnabled(True)
        self.addParameter(color_param)
        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.ELEVATION_MAP,
                description=self.tr("Generate Elevation Overlay (Hillshade)"),
                defaultValue=True,
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterAuthConfig(
                name=self.PROXY_AUTH,
                description=self.tr("Proxy authentication (optional)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT, "Contour lines output"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        self.status_total = 0.0
        self.progress = 0.0
        os.makedirs(self.temp_dir, exist_ok=True)
        feedback.pushInfo("\nTemporary folder: " + self.temp_dir)

        # Load area of interest in EPSG:4326
        area_of_interest = self.parameterAsExtent(
            parameters,
            self.AREA_OF_INTEREST,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        if area_of_interest.isNull() or not area_of_interest.isFinite():
            raise ValueError(
                self.tr(
                    "Invalid area of interest (NaN values detected).\n\n"
                    "Please draw a rectangle directly using the extent tool."
                )
            )

        aoi_geometry = QgsGeometry.fromRect(area_of_interest)
        if aoi_geometry.isNull() or aoi_geometry.isEmpty():
            raise ValueError(self.tr("Could not create the area of interest geometry."))

        aoi_width = area_of_interest.width()
        aoi_height = area_of_interest.height()
        max_extent = 5.0
        if aoi_width > max_extent or aoi_height > max_extent:
            raise ValueError(
                self.tr(
                    "Area of interest is too large ({}° x {}°). Maximum extent is {}°.".format(
                        aoi_width, aoi_height, max_extent
                    )
                )
            )

        # Write AOI shapefile for clipping
        aoi_shp_path = os.path.join(self.temp_dir, "area_of_interest.shp")
        shp_driver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(aoi_shp_path):
            shp_driver.DeleteDataSource(aoi_shp_path)
        aoi_datasource = shp_driver.CreateDataSource(aoi_shp_path)
        aoi_layer = aoi_datasource.CreateLayer("layer", geom_type=ogr.wkbPolygon)
        feat_defn = aoi_layer.GetLayerDefn()
        feature = ogr.Feature(feat_defn)
        wkt = aoi_geometry.asWkt()
        ogr_geom = ogr.CreateGeometryFromWkt(wkt)
        if ogr_geom is None:
            raise ValueError(self.tr("Failed to convert geometry to OGR format."))
        feature.SetGeometry(ogr_geom)
        aoi_layer.CreateFeature(feature)
        aoi_datasource = None

        # Load parameters
        interval = self.parameterAsInt(parameters, self.INTERVAL, context)
        unit_index = self.parameterAsEnum(parameters, self.UNIT, context)
        use_feet = unit_index == 1
        smoothing = self.parameterAsString(parameters, self.SMOOTHING, context)
        color = self.parameterAsColor(parameters, self.COLOR, context)
        generate_elevation_map = self.parameterAsBool(
            parameters, self.ELEVATION_MAP, context
        )

        # Proxy setup
        proxy_opener = None
        auth_id = self.parameterAsString(parameters, self.PROXY_AUTH, context)
        if auth_id:
            import urllib.request
            from urllib.parse import urlparse

            try:
                auth_mgr = QgsApplication.authManager()
                auth_cfg = QgsAuthMethodConfig()
                auth_mgr.loadAuthenticationConfig(auth_id, auth_cfg, True)
                auth_info = auth_cfg.configMap()
                proxy_host = urlparse(auth_info["realm"]).hostname
                proxy_port = urlparse(auth_info["realm"]).port
                proxy_user = auth_info["username"]
                proxy_pass = auth_info["password"]
                proxy_base_url = "http://{}:{}".format(proxy_host, proxy_port)
                proxy_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                proxy_mgr.add_password(None, proxy_base_url, proxy_user, proxy_pass)
                proxy_auth_handler = urllib.request.ProxyBasicAuthHandler(proxy_mgr)
                proxy_handler = urllib.request.ProxyHandler(
                    {"http": proxy_base_url, "https": proxy_base_url}
                )
                proxy_opener = urllib.request.build_opener(
                    proxy_handler, proxy_auth_handler
                )
                feedback.pushInfo("\nUsing proxy authentication")
            except Exception as e:
                feedback.pushInfo(
                    "\nFailed to load proxy auth: " + str(type(e).__name__)
                )

        # Determine required tiles
        south = area_of_interest.yMinimum()
        north = area_of_interest.yMaximum()
        west = area_of_interest.xMinimum()
        east = area_of_interest.xMaximum()

        feedback.pushInfo("\nCalculating required GLO-30 tiles")
        tile_list = required_tiles(south, north, west, east, feedback=feedback)

        if not tile_list:
            feedback.pushInfo("\nNo tiles found for the given area.")
            return {}

        steps = 5 + 2 * len(tile_list)
        self.status_total = 100.0 / steps
        self.progress = 0.0
        self.progress += 1
        feedback.setProgress(int(self.progress * self.status_total))

        # Download tiles
        feedback.pushInfo("\nDownloading DEM tiles")
        tile_paths = download_tiles(
            tile_list,
            temp_dir=self.temp_dir,
            feedback=feedback,
            proxy_opener=proxy_opener,
        )

        if not tile_paths:
            feedback.pushInfo("\nNo tiles downloaded successfully.")
            return {}

        self.progress += len(tile_list)
        feedback.setProgress(int(self.progress * self.status_total))

        # Clip tiles
        feedback.pushInfo("\nClipping tiles to area of interest")
        clipped_rasters = []

        def gdal_callback(info, *args):
            p = self.progress + info
            feedback.setProgress(int(p * self.status_total))

        for tile_path in tile_paths:
            if feedback.isCanceled():
                return {}
            base = os.path.splitext(os.path.basename(tile_path))[0]
            fn_clip = os.path.join(self.temp_dir, base + "_clip.tif")
            clipped_rasters.append(fn_clip)
            feedback.pushInfo("Clipping: " + os.path.basename(tile_path))
            gdal.Warp(
                fn_clip,
                tile_path,
                cutlineDSName=aoi_shp_path,
                cropToCutline=True,
                dstNodata=-32768,
                srcSRS="EPSG:4326",
                dstSRS="EPSG:4326",
                format="GTiff",
                callback=gdal_callback,
            )
            self.progress += 1
            feedback.setProgress(int(self.progress * self.status_total))

        # Merge
        feedback.pushInfo("\nMerging clipped tiles")
        merged_path = os.path.join(self.temp_dir, "merged_contour.tif")
        gdal.Warp(
            merged_path,
            clipped_rasters,
            dstNodata=-32768,
            format="GTiff",
            callback=gdal_callback,
        )

        if feedback.isCanceled():
            return {}
        self.progress += 1
        feedback.setProgress(int(self.progress * self.status_total))

        # Save raw DEM for the optional elevation overlay path.
        elevation_dem_path = None
        if generate_elevation_map:
            elevation_dem_path = os.path.join(self.temp_dir, "elevation_contour.tif")
            shutil.copy2(merged_path, elevation_dem_path)

        # Smooth
        self._smooth_contour_line(smoothing, feedback)
        if feedback.isCanceled():
            return {}
        self.progress += 1
        feedback.setProgress(int(self.progress * self.status_total))

        # Convert to feet if needed
        if use_feet:
            feedback.pushInfo("\nConverting elevation values from metres to feet")
            merged_metres = os.path.join(self.temp_dir, "merged_metres.tif")
            os.replace(merged_path, merged_metres)
            _raster_calc(
                lambda A: A * 3.28084,
                output_path=merged_path,
                nodata=-32768,
                overwrite=True,
                A=merged_metres,
            )

        # Generate contour lines
        feedback.pushInfo("\nGenerating contour lines")
        tmp_shp_dir = tempfile.mkdtemp(dir=self.temp_dir, prefix="contourlines_")
        contour_shp_path = os.path.join(tmp_shp_dir, "contourlines.shp")

        shp_ds = shp_driver.CreateDataSource(contour_shp_path)
        srs_4326 = osr.SpatialReference()
        srs_4326.ImportFromEPSG(4326)
        srs_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        contour_layer = shp_ds.CreateLayer("Contour Lines", srs=srs_4326)
        contour_layer.CreateField(ogr.FieldDefn("ID", ogr.OFTInteger))
        contour_layer.CreateField(ogr.FieldDefn("ELEV", ogr.OFTReal))
        type_field = ogr.FieldDefn("TYPE", ogr.OFTString)
        type_field.SetWidth(50)
        contour_layer.CreateField(type_field)

        merged_ds = gdal.Open(merged_path)
        merged_band = merged_ds.GetRasterBand(1)
        nodata_val = merged_band.GetNoDataValue()
        gdal.ContourGenerate(
            merged_band,
            interval,
            0,
            [],
            1 if nodata_val is not None else 0,
            nodata_val if nodata_val is not None else -32768,
            contour_layer,
            0,
            1,
            callback=gdal_callback,
        )
        shp_ds = None
        merged_ds = None

        if feedback.isCanceled():
            return {}
        self.progress += 1
        feedback.setProgress(int(self.progress * self.status_total))

        # Reproject if needed
        project_crs = context.project().crs()
        if project_crs.isValid() and project_crs.authid().upper() != "EPSG:4326":
            feedback.pushInfo("\nReprojecting contours to " + project_crs.authid())
            reproj_dir = tempfile.mkdtemp(
                dir=self.temp_dir, prefix="contourlines_reproj_"
            )
            reproj_shp_path = os.path.join(reproj_dir, "contourlines_reproj.shp")
            gdal.VectorTranslate(
                reproj_shp_path,
                contour_shp_path,
                options=gdal.VectorTranslateOptions(
                    dstSRS=project_crs.authid(), reproject=True
                ),
            )
            final_shp_path = reproj_shp_path
        else:
            final_shp_path = contour_shp_path

        output_dest = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        if not output_dest:
            raise RuntimeError("No contour output destination was provided.")
        gdal.VectorTranslate(output_dest, final_shp_path)
        final_output_path = output_dest

        # Load contour layer
        unit_label = "ft" if use_feet else "m"
        layer = QgsVectorLayer(
            final_output_path, "Contour Lines ({}{})".format(interval, unit_label)
        )
        feedback.pushInfo(
            "Contour lines generated: " + str(len(list(layer.getFeatures())))
        )

        # Apply symbology
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        root_rule = renderer.rootRule()

        index_rule = root_rule.children()[0]
        index_rule.setLabel("Index Contour")
        index_rule.setFilterExpression(
            '"ELEV" % {itv} < 0.01 OR "ELEV" % {itv} > {itv} - 0.01'.format(
                itv=interval * 5
            )
        )
        index_rule.symbol().setColor(color)
        index_rule.symbol().setWidth(0.5)

        normal_rule = root_rule.children()[0].clone()
        normal_rule.setLabel("Normal Contour")
        normal_rule.setFilterExpression("ELSE")
        normal_rule.symbol().setColor(color)
        normal_rule.symbol().setWidth(0.25)
        root_rule.appendChild(normal_rule)

        layer.setRenderer(renderer)
        layer.triggerRepaint()

        # Apply labels
        mask = QgsTextMaskSettings()
        mask.setSize(2)
        index_contour_rule = root_rule.children()[0]
        mask.setMaskedSymbolLayers(
            [
                QgsSymbolLayerReference(
                    layer.id(),
                    index_contour_rule.symbol().symbolLayer(0).id(),
                )
            ]
        )
        mask.setEnabled(True)

        text_format = QgsTextFormat()
        text_format.setSize(10)
        text_format.setColor(color)
        text_format.setMask(mask)

        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = (
            'CASE WHEN "ELEV" % {itv} < 0.01 OR "ELEV" % {itv} > {itv} - 0.01'
            " THEN \"ELEV\" ELSE '' END"
        ).format(itv=interval * 5)
        label_settings.enabled = True
        label_settings.drawLabels = True
        label_settings.repeatDistance = 50
        label_settings.isExpression = True

        label_settings.placement = Qgis.LabelPlacement.Line
        label_settings.placementFlags = Qgis.LabelLinePlacementFlag.OnLine

        label_settings.setFormat(text_format)
        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        layer.triggerRepaint()

        self.progress += 1
        feedback.setProgress(int(self.progress * self.status_total))

        # Hillshade overlay
        if generate_elevation_map:
            feedback.pushInfo("\nAdding Elevation Overlay layer")
            overlay_raster_path = self._prepare_elevation_overlay_raster(
                elevation_dem_path, context, feedback
            )
            dem_layer = QgsRasterLayer(overlay_raster_path, "Elevation Overlay")
            if dem_layer.isValid():
                from qgis.PyQt.QtGui import QPainter

                dem_layer.setBlendMode(painter_blend_mode_color_dodge(QPainter))
                QgsProject.instance().addMapLayer(dem_layer)
            else:
                feedback.pushInfo("Warning: Could not load Elevation Overlay layer")

        QgsProject.instance().addMapLayer(layer)
        feedback.pushInfo("\nDone.")
        return {self.OUTPUT: final_output_path}

    def _smooth_contour_line(self, smoothing, feedback):
        """Apply Gaussian-weighted contour line smoothing guided by TPI."""
        if smoothing == "None":
            return

        feedback.pushInfo("\nApplying contour line smoothing: " + smoothing)
        path = self.temp_dir
        input_dem = os.path.join(path, "merged_contour.tif")

        # Convert to Float32
        gdal.Translate(
            os.path.join(path, "dem.tif"),
            input_dem,
            outputType=gdal.GDT_Float32,
            noData=-32768,
        )

        # 3x3 Gaussian blur VRT
        _make_blur_vrt(
            os.path.join(path, "dem_blur_3x3.vrt"),
            os.path.join(path, "dem.tif"),
            kernel_size=3,
        )

        feedback.setProgress(int((self.progress + 0.2) * self.status_total))

        # TPI
        gdal.DEMProcessing(
            destName=os.path.join(path, "dem_tpi.tif"),
            srcDS=input_dem,
            processing="TPI",
        )
        _raster_calc(
            lambda A: np.abs(A),
            output_path=os.path.join(path, "tpi_pos.tif"),
            nodata=-32768,
            overwrite=True,
            A=os.path.join(path, "dem_tpi.tif"),
        )

        feedback.setProgress(int((self.progress + 0.4) * self.status_total))

        # 9x9 Gaussian blur for TPI
        _make_blur_vrt(
            os.path.join(path, "tpi_blur_3x3.vrt"),
            os.path.join(path, "tpi_pos.tif"),
            kernel_size=9,
        )

        feedback.setProgress(int((self.progress + 0.6) * self.status_total))

        # Normalise TPI
        vrt_path = os.path.join(path, "tpi_blur_3x3.vrt")
        if not os.path.exists(vrt_path):
            raise FileNotFoundError("File not found: " + vrt_path)
        vrt_ds = gdal.Open(vrt_path)
        max_val = None
        if vrt_ds is not None:
            stats = vrt_ds.GetRasterBand(1).GetStatistics(True, True)
            if stats and stats[1] is not None and stats[1] != 0:
                max_val = stats[1]
            vrt_ds = None
        try:
            if max_val is not None and max_val != 0:
                _raster_calc(
                    lambda A: A / max_val,
                    output_path=os.path.join(path, "tpi_norm.tif"),
                    nodata=-32768,
                    overwrite=True,
                    A=vrt_path,
                )
            else:
                logger.warning("Could not get TPI statistics, using raw TPI")
                gdal.Translate(
                    destName=os.path.join(path, "tpi_norm.tif"), srcDS=vrt_path
                )
        except Exception:
            logger.warning("TPI normalisation failed, using raw TPI")
            gdal.Translate(destName=os.path.join(path, "tpi_norm.tif"), srcDS=vrt_path)

        feedback.setProgress(int((self.progress + 0.8) * self.status_total))

        # Blend DEM with smoothed versions
        if smoothing == "Low":
            # Blend 3x3 blur (B) with original DEM (C) guided by TPI (A)
            _raster_calc(
                lambda A, B, C: A * B + (1 - A) * C,
                output_path=os.path.join(path, "merged_contour.tif"),
                nodata=-32768,
                overwrite=True,
                A=os.path.join(path, "tpi_norm.tif"),
                B=os.path.join(path, "dem_blur_3x3.vrt"),
                C=os.path.join(path, "dem.tif"),
            )
        elif smoothing == "Medium":
            _make_blur_vrt(
                os.path.join(path, "dem_blur_7x7.vrt"),
                os.path.join(path, "dem.tif"),
                kernel_size=7,
            )
            _raster_calc(
                lambda A, B, C: A * B + (1 - A) * C,
                output_path=os.path.join(path, "merged_contour.tif"),
                nodata=-32768,
                overwrite=True,
                A=os.path.join(path, "tpi_norm.tif"),
                B=os.path.join(path, "dem_blur_3x3.vrt"),
                C=os.path.join(path, "dem_blur_7x7.vrt"),
            )
        else:  # High
            _make_blur_vrt(
                os.path.join(path, "dem_blur_13x13.vrt"),
                os.path.join(path, "dem.tif"),
                kernel_size=13,
            )
            _raster_calc(
                lambda A, B, C: A * B + (1 - A) * C,
                output_path=os.path.join(path, "merged_contour.tif"),
                nodata=-32768,
                overwrite=True,
                A=os.path.join(path, "tpi_norm.tif"),
                B=os.path.join(path, "dem_blur_3x3.vrt"),
                C=os.path.join(path, "dem_blur_13x13.vrt"),
            )

        feedback.setProgress(int((self.progress + 1.0) * self.status_total))

    def _prepare_elevation_overlay_raster(self, source_dem_path, context, feedback):
        """Build a lighter hillshade raster so the overlay draws quickly in QGIS."""
        feedback.pushInfo("Optimizing overlay raster for display...")

        source_ds = gdal.Open(source_dem_path)
        if source_ds is None:
            raise RuntimeError("Could not open overlay DEM: " + source_dem_path)

        src_width = source_ds.RasterXSize
        src_height = source_ds.RasterYSize
        source_ds = None

        overlay_width, overlay_height, scale = choose_overlay_dimensions(
            src_width, src_height
        )
        overlay_dem_path = os.path.join(self.temp_dir, "elevation_overlay_dem.tif")
        overlay_hillshade_path = os.path.join(
            self.temp_dir, "elevation_overlay_hillshade.tif"
        )

        project_crs = context.project().crs()
        dst_srs = "EPSG:4326"
        if project_crs.isValid():
            dst_srs = project_crs.authid()

        if scale < 1.0:
            feedback.pushInfo(
                "Downsampling overlay raster from {}x{} to {}x{} for faster display.".format(
                    src_width, src_height, overlay_width, overlay_height
                )
            )

        translate_result = gdal.Warp(
            overlay_dem_path,
            source_dem_path,
            format="GTiff",
            dstNodata=-32768,
            dstSRS=dst_srs,
            width=overlay_width,
            height=overlay_height,
            resampleAlg=gdal.GRA_Bilinear,
            multithread=True,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"],
        )
        if translate_result is None:
            raise RuntimeError("Failed to prepare optimized overlay raster.")
        translate_result = None

        hillshade_result = gdal.DEMProcessing(
            overlay_hillshade_path,
            overlay_dem_path,
            "hillshade",
            format="GTiff",
            azimuth=315,
            altitude=45,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"],
        )
        if hillshade_result is None:
            raise RuntimeError("Failed to generate optimized hillshade overlay.")
        hillshade_result = None

        overview_levels = build_overview_levels(overlay_width, overlay_height)
        if overview_levels:
            feedback.pushInfo(
                "Building overlay pyramids: {}".format(
                    ", ".join(str(level) for level in overview_levels)
                )
            )
            hillshade_ds = gdal.Open(overlay_hillshade_path, gdal.GA_Update)
            if hillshade_ds is not None:
                hillshade_ds.BuildOverviews("AVERAGE", overview_levels)
                hillshade_ds = None

        return overlay_hillshade_path

    def name(self):
        return "contour_lines"

    def displayName(self):
        return self.tr("Contour Lines")

    def group(self):
        return self.tr("Terrain Analysis")

    def groupId(self):
        return "terrain_analysis"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ContourLinesAlgorithm()
