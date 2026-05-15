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

from ._geo_utils import _interpolate_longitudes_shortest, sample_line_from_grid  # noqa: F401 re-export
from .constants import BYTES_PER_MEBIBYTE, EARTH_RADIUS_M

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
    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d_r)
        + math.cos(lat_r) * math.sin(d_r) * math.cos(brng)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brng) * math.sin(d_r) * math.cos(lat_r),
        math.cos(d_r) - math.sin(lat_r) * math.sin(lat2),
    )
    lon_deg = (math.degrees(lon2) + 540.0) % 360.0 - 180.0
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
                self.data = self.data[::-1].copy()
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
        assert self.data is not None, "ElevationGrid closed"
        # max_lat is the top-edge latitude (geotransform origin), not cell center.
        # The -0.5 shift maps from cell edge to cell center for bilinear lookup.
        fy = (self.max_lat - lat) / self.d_lat - 0.5
        fx = (lon - self.min_lon) / self.d_lon - 0.5
        if fy < -0.5 or fx < -0.5 or fy > self.n_rows - 0.5 or fx > self.n_cols - 0.5:
            return float("nan")
        fy = max(0.0, min(self.n_rows - 1.0, fy))
        fx = max(0.0, min(self.n_cols - 1.0, fx))
        y0 = int(fy)
        x0 = int(fx)
        y1 = min(y0 + 1, self.n_rows - 1)
        x1 = min(x0 + 1, self.n_cols - 1)
        ty = fy - y0
        tx = fx - x0
        v00 = self.data[y0, x0]
        v01 = self.data[y0, x1]
        v10 = self.data[y1, x0]
        v11 = self.data[y1, x1]
        return (  # type: ignore[no-any-return]
            v00 * (1 - tx) * (1 - ty)
            + v01 * tx * (1 - ty)
            + v10 * (1 - tx) * ty
            + v11 * tx * ty
        )

    def sample_line(self, lat1, lon1, lat2, lon2, n_points):
        assert self.data is not None, "ElevationGrid closed"
        ts = np.linspace(0.0, 1.0, n_points)
        lats = lat1 + ts * (lat2 - lat1)
        lons = _interpolate_longitudes_shortest(lon1, lon2, ts)
        fy_raw = (self.max_lat - lats) / self.d_lat - 0.5
        fx_raw = (lons - self.min_lon) / self.d_lon - 0.5
        oob = (
            (fy_raw < -0.5) | (fx_raw < -0.5)
            | (fy_raw > self.n_rows - 0.5) | (fx_raw > self.n_cols - 0.5)
        )
        fy = np.clip(fy_raw, 0.0, self.n_rows - 1.0 - 1e-9)
        fx = np.clip(fx_raw, 0.0, self.n_cols - 1.0 - 1e-9)
        y0 = np.floor(fy).astype(np.int32)
        x0 = np.floor(fx).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, self.n_rows - 1)
        x1 = np.clip(x0 + 1, 0, self.n_cols - 1)
        ty = (fy - y0).astype(np.float32)
        tx_ = (fx - x0).astype(np.float32)
        result = (
            self.data[y0, x0] * (1 - tx_) * (1 - ty)
            + self.data[y0, x1] * tx_ * (1 - ty)
            + self.data[y1, x0] * (1 - tx_) * ty
            + self.data[y1, x1] * tx_ * ty
        )
        result[oob] = np.nan
        return result

    def sample_grid(self, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        assert self.data is not None, "ElevationGrid closed"
        """Sample the DEM at every (lat, lon) grid intersection.

        Returns a float32 array of shape (len(lats), len(lons)).
        Out-of-bounds or no-data cells are NaN.
        """
        lats_arr = np.asarray(lats, dtype=np.float64)[:, np.newaxis]
        lons_arr = np.asarray(lons, dtype=np.float64)[np.newaxis, :]
        fy_raw = (self.max_lat - lats_arr) / self.d_lat - 0.5
        fx_raw = (lons_arr - self.min_lon) / self.d_lon - 0.5
        oob = (
            (fy_raw < -0.5) | (fx_raw < -0.5)
            | (fy_raw > self.n_rows - 0.5) | (fx_raw > self.n_cols - 0.5)
        )
        fy = np.clip(fy_raw, 0.0, self.n_rows - 1.0 - 1e-9)
        fx = np.clip(fx_raw, 0.0, self.n_cols - 1.0 - 1e-9)
        y0 = np.floor(fy).astype(np.int32)
        x0 = np.floor(fx).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, self.n_rows - 1)
        x1 = np.clip(x0 + 1, 0, self.n_cols - 1)
        ty = (fy - y0).astype(np.float32)
        tx_ = (fx - x0).astype(np.float32)
        result = (
            self.data[y0, x0] * (1 - tx_) * (1 - ty)
            + self.data[y0, x1] * tx_ * (1 - ty)
            + self.data[y1, x0] * (1 - tx_) * ty
            + self.data[y1, x1] * tx_ * ty
        ).astype(np.float32)
        result[oob] = np.nan
        return result  # type: ignore[no-any-return]

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
        self.data = None  # type: ignore[assignment]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        if self.data is not None:
            self.close()



