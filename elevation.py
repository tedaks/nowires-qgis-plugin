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


Elevation grid with bilinear sampling, terrain profile generation,
and geographic utilities.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

import logging
import math

import numpy as np

from osgeo import gdal

logger = logging.getLogger(__name__)


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def bearing_destination(lat, lon, bearing_deg_val, dist_m):
    R = 6371000.0
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
    return math.degrees(lat2), math.degrees(lon2)


class ElevationGrid:
    """Dense elevation grid with bilinear sampling."""

    def __init__(self, dem_path):
        ds = gdal.Open(dem_path)
        if ds is None:
            raise RuntimeError("Cannot open DEM: {}".format(dem_path))

        try:
            self.transform = ds.GetGeoTransform()
            self.projection = ds.GetProjection()
            band = ds.GetRasterBand(1)
            self.nodata = band.GetNoDataValue()

            data = band.ReadAsArray(
                buf_xsize=ds.RasterXSize,
                buf_ysize=ds.RasterYSize,
                buf_type=gdal.GDT_Float32,
            )
            if data is None:
                raise RuntimeError("Failed to read DEM band: {}".format(dem_path))
            self.data = np.asarray(data, dtype=np.float32)
            if self.nodata is not None:
                self.data[self.data == self.nodata] = 0.0

            self.n_rows, self.n_cols = self.data.shape
            self.min_lon = self.transform[0]
            self.max_lon = self.min_lon + self.transform[1] * self.n_cols
            self.min_lat = self.transform[3] + self.transform[5] * self.n_rows
            self.max_lat = self.transform[3]
            if self.min_lat > self.max_lat:
                self.min_lat, self.max_lat = self.max_lat, self.min_lat

            self.d_lat = (self.max_lat - self.min_lat) / max(self.n_rows - 1, 1)
            self.d_lon = (self.max_lon - self.min_lon) / max(self.n_cols - 1, 1)
        finally:
            ds = None

        logger.info(
            "ElevationGrid: %s shape=%s bounds=(%.4f,%.4f)-(%.4f,%.4f) %.1f MB",
            dem_path,
            self.data.shape,
            self.min_lat,
            self.min_lon,
            self.max_lat,
            self.max_lon,
            self.data.nbytes / 1048576.0,
        )

    def sample(self, lat, lon):
        fy = (self.max_lat - lat) / self.d_lat
        fx = (lon - self.min_lon) / self.d_lon
        if fy < 0 or fx < 0 or fy > self.n_rows - 1 or fx > self.n_cols - 1:
            return 0.0
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
        return (
            v00 * (1 - tx) * (1 - ty)
            + v01 * tx * (1 - ty)
            + v10 * (1 - tx) * ty
            + v11 * tx * ty
        )

    def sample_line(self, lat1, lon1, lat2, lon2, n_points):
        ts = np.linspace(0.0, 1.0, n_points)
        lats = lat1 + ts * (lat2 - lat1)
        lons = lon1 + ts * (lon2 - lon1)
        fy = np.clip(
            (self.max_lat - lats) / self.d_lat, 0, self.n_rows - 1 - 1e-9
        )
        fx = np.clip((lons - self.min_lon) / self.d_lon, 0, self.n_cols - 1 - 1e-9)
        y0 = np.floor(fy).astype(np.int32)
        x0 = np.floor(fx).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, self.n_rows - 1)
        x1 = np.clip(x0 + 1, 0, self.n_cols - 1)
        ty = (fy - y0).astype(np.float32)
        tx_ = (fx - x0).astype(np.float32)
        return (
            self.data[y0, x0] * (1 - tx_) * (1 - ty)
            + self.data[y0, x1] * tx_ * (1 - ty)
            + self.data[y1, x0] * (1 - tx_) * ty
            + self.data[y1, x1] * tx_ * ty
        )

    def terrain_profile(self, lat1, lon1, lat2, lon2, step_m=30.0):
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

    def grid_meta_dict(self):
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "n_lat": self.n_rows,
            "n_lon": self.n_cols,
        }


def sample_line_from_grid(gd, gm, lat1, lon1, lat2, lon2, n_pts):
    min_lat = gm["min_lat"]
    max_lat = gm["max_lat"]
    min_lon = gm["min_lon"]
    max_lon = gm["max_lon"]
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (max_lat - min_lat) / max(n_lat - 1, 1)
    d_lon = (max_lon - min_lon) / max(n_lon - 1, 1)

    ts = np.linspace(0.0, 1.0, n_pts)
    lats = lat1 + ts * (lat2 - lat1)
    lons = lon1 + ts * (lon2 - lon1)

    fy = np.clip((max_lat - lats) / d_lat, 0, n_lat - 1 - 1e-9)
    fx = np.clip((lons - min_lon) / d_lon, 0, n_lon - 1 - 1e-9)

    y0 = np.floor(fy).astype(np.int32)
    x0 = np.floor(fx).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, n_lat - 1)
    x1 = np.clip(x0 + 1, 0, n_lon - 1)
    ty = (fy - y0).astype(np.float32)
    tx_ = (fx - x0).astype(np.float32)

    return (
        gd[y0, x0] * (1 - tx_) * (1 - ty)
        + gd[y0, x1] * tx_ * (1 - ty)
        + gd[y1, x0] * (1 - tx_) * ty
        + gd[y1, x1] * tx_ * ty
    )
