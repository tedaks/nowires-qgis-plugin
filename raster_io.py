# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from osgeo import gdal, osr

from qgis.core import QgsProcessingException

from NoWires.constants import COVERAGE_NODATA
from NoWires.radio_coverage.compute import grid_to_raster_array


def write_geotiff(path, grid, min_lat, max_lat, min_lon, max_lon, nodata=COVERAGE_NODATA):
    """Write a 2D numpy grid to a single-band float32 GeoTIFF in EPSG:4326.

    The grid is passed through grid_to_raster_array for the row-orientation
    flip the QGIS pipeline expects.

    **Axis convention**: ``grid`` uses (i=0 → southernmost latitude) indexing.
    grid_to_raster_array flips the rows with [::-1] so that `raster[0]`
    corresponds to the northernmost latitude, matching GDAL's north-up
    geotransform (origin = north-west corner).  Any change to the axis
    ordering in coverage_tasks / coverage_engine must be reflected here.
    """
    raster = grid_to_raster_array(grid)
    n_rows, n_cols = raster.shape
    driver = gdal.GetDriverByName("GTiff")
    if driver is None:
        raise QgsProcessingException("GDAL GTiff driver not available")
    ds = driver.Create(path, n_cols, n_rows, 1, gdal.GDT_Float32)
    if ds is None:
        raise QgsProcessingException("GDAL failed to create GeoTIFF: {}".format(path))
    band = None
    try:
        ds.SetGeoTransform([
            min_lon, (max_lon - min_lon) / n_cols, 0,
            max_lat, 0, -(max_lat - min_lat) / n_rows,
        ])
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(nodata)
        if band.WriteArray(raster) != 0:
            raise QgsProcessingException(
                "WriteArray failed writing GeoTIFF: {}".format(path))
        band.FlushCache()
    finally:
        del band
        del ds
