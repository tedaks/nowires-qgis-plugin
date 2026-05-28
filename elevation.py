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


Elevation grid with bilinear sampling, terrain profile generation,
and geographic utilities.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

from __future__ import annotations

import logging
import math

import numpy as np

from osgeo import gdal

from NoWires._bilinear import bilinear_sample, bilinear_sample_grid
from NoWires._geo_utils import _interpolate_longitudes_shortest, sample_line_from_grid  # noqa: F401 re-export
from NoWires.constants import BYTES_PER_MEBIBYTE, EARTH_RADIUS_M

logger = logging.getLogger(__name__)


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = EARTH_RADIUS_M
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    a = max(0.0, min(1.0, a))
    result: float = 2 * R * math.asin(math.sqrt(a))
    return result


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def bearing_destination(lat, lon, bearing_deg_val, dist_m) -> tuple[float, float]:
    R = EARTH_RADIUS_M
    brng = math.radians(bearing_deg_val)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    d_r = dist_m / R
    a = math.sin(lat_r) * math.cos(d_r) + math.cos(lat_r) * math.sin(d_r) * math.cos(brng)
    lat2 = math.asin(max(-1.0, min(1.0, a)))
    lon2 = lon_r + math.atan2(
        math.sin(brng) * math.sin(d_r) * math.cos(lat_r),
        math.cos(d_r) - math.sin(lat_r) * math.sin(lat2),
    )
    lon_deg = ((math.degrees(lon2) + 180.0) % 360.0) - 180.0
    return math.degrees(lat2), lon_deg


class ElevationGrid:
    """Dense elevation grid with bilinear sampling.

    Supports the context manager protocol so callers can ensure the
    underlying GDAL dataset is released promptly::

        with ElevationGrid(path) as eg:
            val = eg.sample(lat, lon)
    """

    def __init__(self, dem_path: str) -> None:
        ds = gdal.Open(dem_path)
        if ds is None:
            raise RuntimeError("Cannot open DEM: {}".format(dem_path))

        try:
            transform = ds.GetGeoTransform()
            projection = ds.GetProjection()
            band = ds.GetRasterBand(1)
            nodata = band.GetNoDataValue()

            data = band.ReadAsArray(
                buf_xsize=ds.RasterXSize,
                buf_ysize=ds.RasterYSize,
                buf_type=gdal.GDT_Float32,
            )
            if data is None:
                raise RuntimeError("Failed to read DEM band: {}".format(dem_path))
            self.data: np.ndarray | None = np.asarray(data, dtype=np.float32)
            if nodata is not None:
                self.data[self.data == nodata] = np.nan

            self.n_rows, self.n_cols = self.data.shape
            if self.n_rows == 0 or self.n_cols == 0:
                raise RuntimeError(
                    "DEM raster has zero rows/cols: {}".format(dem_path))
            self.min_lon = transform[0]
            self.max_lon = self.min_lon + transform[1] * self.n_cols
            self.min_lat = transform[3] + transform[5] * self.n_rows
            self.max_lat = transform[3]
            origin_is_north_up = self.min_lat < self.max_lat
            if not origin_is_north_up:
                # South-up raster: row 0 corresponds to the southernmost
                # latitude, which breaks our (max_lat - lat) indexing that
                # assumes row 0 = northernmost.  Flip the data rows so the
                # array is in north-up order, matching Copernicus GLO-30 and
                # ESA WorldCover conventions.
                logger.warning(
                    "DEM %s is south-up; flipping rows to north-up order. "
                    "All Copernicus GLO-30 and ESA WorldCover rasters are "
                    "north-up. If using a custom south-up DEM, verify that "
                    "latitude indexing is correct after this flip.",
                    dem_path,
                )
                self.data = np.ascontiguousarray(self.data[::-1])
                self.min_lat, self.max_lat = self.max_lat, self.min_lat

            self.d_lat = (self.max_lat - self.min_lat) / self.n_rows
            self.d_lon = (self.max_lon - self.min_lon) / self.n_cols
            self.transform = transform
            self.projection = projection
            self.nodata = nodata
        finally:
            # Release band before dataset per GDAL best practice.
            del band
            # Release the GDAL dataset handle promptly after reading data.
            # The numpy array (self.data) is an independent copy, so
            # closing the dataset does not affect subsequent sampling.
            del ds

        logger.info(
            "ElevationGrid: %s shape=%s bounds=(%.4f,%.4f)-(%.4f,%.4f) %.1f MB",
            dem_path,
            self.data.shape,
            self.min_lat,
            self.min_lon,
            self.max_lat,
            self.max_lon,
            self.data.nbytes / BYTES_PER_MEBIBYTE,
        )

    def sample(self, lat: float, lon: float) -> float:
        if self.data is None:
            raise RuntimeError("ElevationGrid closed")
        return bilinear_sample(self.data, self.grid_meta_dict(), lat, lon)  # type: ignore[no-any-return]

    def sample_line(self, lat1, lon1, lat2, lon2, n_points):
        if self.data is None:
            raise RuntimeError("ElevationGrid closed")
        ts = np.linspace(0.0, 1.0, n_points)
        lats = lat1 + ts * (lat2 - lat1)
        lons = _interpolate_longitudes_shortest(lon1, lon2, ts)
        return bilinear_sample(self.data, self.grid_meta_dict(), lats, lons)

    def sample_grid(self, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        if self.data is None:
            raise RuntimeError("ElevationGrid closed")
        return bilinear_sample_grid(self.data, self.grid_meta_dict(), lats, lons)  # type: ignore[no-any-return]

    def terrain_profile(self, lat1, lon1, lat2, lon2, step_m=30.0) -> list[tuple[float, float]]:
        dist = haversine_m(lat1, lon1, lat2, lon2)
        if dist < step_m:
            step_m = dist / 3.0 if dist > 0 else 1.0
        n_steps = max(2, int(round(dist / step_m)))
        elevs = self.sample_line(lat1, lon1, lat2, lon2, n_steps + 1)
        result = []
        for i in range(len(elevs)):
            t = i / n_steps
            d = t * dist
            result.append((d, float(elevs[i])))
        return result

    def grid_meta_dict(self) -> dict:
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "n_lat": self.n_rows,
            "n_lon": self.n_cols,
        }

    def close(self) -> None:
        """Release the DEM data array and GDAL dataset handle to free memory."""
        self.data = None  # type: ignore[assignment]  # deliberate ndarray release after close() to free memory

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        try:
            if self.data is not None:
                self.close()
        except (TypeError, AttributeError):
            pass



