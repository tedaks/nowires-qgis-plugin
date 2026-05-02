from osgeo import gdal, osr

from qgis.core import QgsProcessingException

from .coverage_compute import grid_to_raster_array


def write_geotiff(path, grid, min_lat, max_lat, min_lon, max_lon, nodata=-9999.0):
    """Write a 2D numpy grid to a single-band float32 GeoTIFF in EPSG:4326.

    The grid is passed through grid_to_raster_array for the row-orientation
    flip the QGIS pipeline expects.
    """
    raster = grid_to_raster_array(grid)
    n_rows, n_cols = raster.shape
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, n_cols, n_rows, 1, gdal.GDT_Float32)
    if ds is None:
        raise QgsProcessingException("Failed to create GeoTIFF: {}".format(path))
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
        band.WriteArray(raster)
        band.FlushCache()
    finally:
        ds = None