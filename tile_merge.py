# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import logging
import os

from osgeo import gdal, ogr, osr

from NoWires.constants import GDAL_DRIVER_NAME
from NoWires.geo_bounds import longitude_intervals
from NoWires.report.markers import remove_existing_ogr_dataset

logger = logging.getLogger(__name__)


def _rectangle_geometry(south, north, west, east, ogr_module=ogr):
    ring = ogr_module.Geometry(ogr_module.wkbLinearRing)
    ring.AddPoint(west, south)
    ring.AddPoint(east, south)
    ring.AddPoint(east, north)
    ring.AddPoint(west, north)
    ring.AddPoint(west, south)
    poly = ogr_module.Geometry(ogr_module.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def _aoi_geometry_for_bounds(south, north, west, east, ogr_module=ogr):
    intervals = longitude_intervals(west, east)
    if len(intervals) == 1:
        return _rectangle_geometry(south, north, intervals[0][0], intervals[0][1], ogr_module)
    geom = ogr_module.Geometry(ogr_module.wkbMultiPolygon)
    for lon_west, lon_east in intervals:
        geom.AddGeometry(
            _rectangle_geometry(south, north, lon_west, lon_east, ogr_module))
    return geom


def clip_and_merge_tiles(
    tile_paths, south, north, west, east, temp_dir, feedback,
    nodata_value, aoi_prefix, merge_filename,
):
    if not tile_paths:
        return None

    aoi_shp = os.path.join(temp_dir, aoi_prefix + "_aoi_clip.shp")
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    remove_existing_ogr_dataset(shp_driver, aoi_shp)
    ds = None
    try:
        ds = shp_driver.CreateDataSource(aoi_shp)
        if ds is None:
            raise RuntimeError("Failed to create dataset at {}".format(aoi_shp))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        layer = ds.CreateLayer("aoi", srs=srs, geom_type=ogr.wkbPolygon)
        feat_defn = layer.GetLayerDefn()
        feature = ogr.Feature(feat_defn)
        feature.SetGeometry(_aoi_geometry_for_bounds(south, north, west, east))
        layer.CreateFeature(feature)
        feature = None
    finally:
        ds = None

    clipped = []
    for path in tile_paths:
        if feedback and feedback.isCanceled():
            return None
        base = os.path.splitext(os.path.basename(path))[0]
        clip_path = os.path.join(temp_dir, base + "_clip.tif")

        if feedback:
            feedback.pushInfo("Clipping: " + os.path.basename(path))

        result = gdal.Warp(
            clip_path,
            path,
            cutlineDSName=aoi_shp,
            cropToCutline=True,
            dstNodata=nodata_value,
            srcSRS="EPSG:4326",
            dstSRS="EPSG:4326",
            format=GDAL_DRIVER_NAME,
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        if result is None:
            logger.warning("Warp failed for %s", os.path.basename(path))
            continue
        result = None

        check = gdal.Open(clip_path)
        if check is None or check.GetRasterBand(1).ComputeStatistics(False) is None:
            logger.warning("Empty or invalid clip for %s", os.path.basename(path))
            check = None
            continue
        check = None
        clipped.append(clip_path)

    if not clipped:
        return None

    merged_path = os.path.join(temp_dir, merge_filename)
    if feedback:
        feedback.pushInfo("Merging {} clipped tiles".format(len(clipped)))
    result = gdal.Warp(
        merged_path, clipped, dstNodata=nodata_value, format=GDAL_DRIVER_NAME,
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )
    if result is None:
        logger.error("Merge Warp failed")
        return None
    result = None
    remove_existing_ogr_dataset(shp_driver, aoi_shp)
    return merged_path
