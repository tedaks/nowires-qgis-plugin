# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""LandCoverGrid — vectorised raster sampling for clutter correction.

Extracted from clutter.py to keep file sizes under 300 lines and to
provide a vectorised advanced-mode category lookup that avoids a Python-level
per-pixel loop over the raster.
"""

import logging

import numpy as np
from osgeo import gdal

from .clutter_categories import legacy_to_advanced_override, worldcover_class_to_advanced_category

logger = logging.getLogger(__name__)

_LEGACY_CLUTTER_CATEGORIES = ("open", "rural", "vegetation", "suburban", "urban")
_LEGACY_CLUTTER_LOSS_DB = {
    "open": 0.0,
    "rural": 2.0,
    "vegetation": 6.0,
    "suburban": 8.0,
    "urban": 10.0,
}
_CATEGORY_IDX = {k: i for i, k in enumerate(_LEGACY_CLUTTER_CATEGORIES)}
_CLUTTER_LOSS_ARRAY = np.array([
    _LEGACY_CLUTTER_LOSS_DB["open"],
    _LEGACY_CLUTTER_LOSS_DB["rural"],
    _LEGACY_CLUTTER_LOSS_DB["vegetation"],
    _LEGACY_CLUTTER_LOSS_DB["suburban"],
    _LEGACY_CLUTTER_LOSS_DB["urban"],
], dtype=np.float64)

# Lookup table: ESA WorldCover class ID (0-255) -> legacy category index (0-4).
# CAUTION: This LUT and _WORLDCOVER_ADVANCED_IDX in this file must stay consistent
# with _WORLDVER_MAP in clutter_categories.py and _WORLDCOVER_TO_CATEGORY in
# clutter.py. When updating any, update all and run the dual-mapping consistency
# test in test_clutter_categories.py.
_WORLDCOVER_TO_CATEGORY = np.zeros(256, dtype=np.int32)
_WORLDCOVER_TO_CATEGORY[10] = 2
_WORLDCOVER_TO_CATEGORY[20] = 1
_WORLDCOVER_TO_CATEGORY[95] = 2
_WORLDCOVER_TO_CATEGORY[100] = 1
_WORLDCOVER_TO_CATEGORY[30] = 1
_WORLDCOVER_TO_CATEGORY[40] = 1
_WORLDCOVER_TO_CATEGORY[50] = 4
_WORLDCOVER_TO_CATEGORY[60] = 0
_WORLDCOVER_TO_CATEGORY[70] = 0
_WORLDCOVER_TO_CATEGORY[80] = 0
_WORLDCOVER_TO_CATEGORY[90] = 0

_ADVANCED_CATEGORIES = (
    "open",
    "open_rural",
    "dense_rural",
    "vegetation",
    "suburban",
    "urban",
)
_ADVANCED_CAT_IDX = {k: i for i, k in enumerate(_ADVANCED_CATEGORIES)}

_WORLDCOVER_TO_ADVANCED_IDX = np.zeros(256, dtype=np.int32)
_WORLDCOVER_TO_ADVANCED_IDX[10] = _ADVANCED_CAT_IDX["vegetation"]
_WORLDCOVER_TO_ADVANCED_IDX[20] = _ADVANCED_CAT_IDX["dense_rural"]
_WORLDCOVER_TO_ADVANCED_IDX[30] = _ADVANCED_CAT_IDX["open_rural"]
_WORLDCOVER_TO_ADVANCED_IDX[40] = _ADVANCED_CAT_IDX["open_rural"]
_WORLDCOVER_TO_ADVANCED_IDX[50] = _ADVANCED_CAT_IDX["urban"]
_WORLDCOVER_TO_ADVANCED_IDX[60] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[70] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[80] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[90] = _ADVANCED_CAT_IDX["open"]
_WORLDCOVER_TO_ADVANCED_IDX[95] = _ADVANCED_CAT_IDX["vegetation"]
_WORLDCOVER_TO_ADVANCED_IDX[100] = _ADVANCED_CAT_IDX["dense_rural"]


class LandCoverGrid:
    """Raster-backed land-cover sampler with vectorised category lookup."""

    __slots__ = ("data", "min_lat", "max_lat", "min_lon", "max_lon", "nodata", "source")

    def __init__(self, data, min_lat, max_lat, min_lon, max_lon, nodata, source):
        self.data = data
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.nodata = nodata
        self.source = source

    @classmethod
    def from_raster(cls, path):
        ds = gdal.Open(path)
        if ds is None:
            raise RuntimeError("Cannot open land-cover raster: {}".format(path))
        try:
            transform = ds.GetGeoTransform()
            band = ds.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            data = band.ReadAsArray()
            if data is None:
                raise RuntimeError("Failed to read land-cover raster: {}".format(path))
            data = np.asarray(data)
            n_rows, n_cols = data.shape
            min_lon = transform[0]
            max_lon = min_lon + transform[1] * n_cols
            min_lat = transform[3] + transform[5] * n_rows
            max_lat = transform[3]
            if min_lat > max_lat:
                logger.warning(
                    "Land-cover raster %s appears to be south-up; row ordering may be "
                    "inverted. All ESA WorldCover rasters are north-up. If using a custom "
                    "land-cover raster, verify that latitude indexing is correct.",
                    path,
                )
                min_lat, max_lat = max_lat, min_lat
            return cls(data, min_lat, max_lat, min_lon, max_lon, nodata, str(path))
        finally:
            band = None
            ds = None

    def close(self):
        """Release land-cover data to free memory."""
        self.data = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _check_open(self):
        if self.data is None:
            raise RuntimeError(
                "LandCoverGrid has been closed; sampling is no longer possible. "
                "Use the context manager to ensure the grid remains open, or avoid "
                "calling close() before sampling."
            )

    def sample_class(self, lat, lon) -> int | None:
        self._check_open()
        if not (self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon):
            return None
        n_rows, n_cols = self.data.shape
        d_lat = (self.max_lat - self.min_lat) / n_rows
        d_lon = (self.max_lon - self.min_lon) / n_cols
        y = min(int((self.max_lat - lat) / d_lat), n_rows - 1)
        x = min(int((lon - self.min_lon) / d_lon), n_cols - 1)
        value = self.data[y, x]
        if self.nodata is not None and float(value) == self.nodata:
            return None
        return int(value)

    def sample_category(self, lat, lon) -> str | None:
        class_id = self.sample_class(lat, lon)
        if class_id is None:
            return None
        return _LEGACY_CLUTTER_CATEGORIES[_WORLDCOVER_TO_CATEGORY[class_id % 256]]

    def sample_category_grid(self, lats, lons, rx_override=None, context=None):
        """Vectorised category-grid sampling returning losses or category arrays.

        In simple mode (context is None or context.model != "advanced"),
        returns an (n, m) float64 array of per-pixel clutter losses in dB.

        In advanced mode, returns an (n, m) object array of advanced category
        strings, suitable for batch model evaluation by the caller.

        When rx_override is provided, the entire grid is set to that override
        value (for simple mode) or its advanced-mapped equivalent (for
        advanced mode). In coverage analysis every grid cell represents an RX
        location, so rx_override correctly applies across the whole grid.
        """
        from .clutter_advanced import _legacy_to_advanced_override

        n = len(lats)
        m = len(lons)
        advanced = context is not None and context.model == "advanced"

        if self.data is None:
            raise RuntimeError(
                "LandCoverGrid has been closed; sampling is no longer possible. "
                "Use the context manager to ensure the grid remains open, or avoid "
                "calling close() before sampling."
            )

        n_rows, n_cols = self.data.shape
        d_lat = (self.max_lat - self.min_lat) / n_rows
        d_lon = (self.max_lon - self.min_lon) / n_cols
        lat_arr = np.asarray(lats, dtype=np.float64)
        lon_arr = np.asarray(lons, dtype=np.float64)
        y_idx = np.clip(((self.max_lat - lat_arr) / d_lat).astype(np.int32), 0, n_rows - 1)
        x_idx = np.clip(((lon_arr - self.min_lon) / d_lon).astype(np.int32), 0, n_cols - 1)
        sampled = self.data[y_idx[:, np.newaxis], x_idx[np.newaxis, :]]

        lat_oob = (lat_arr < self.min_lat) | (lat_arr > self.max_lat)
        lon_oob = (lon_arr < self.min_lon) | (lon_arr > self.max_lon)
        out_of_bounds = lat_oob[:, np.newaxis] | lon_oob[np.newaxis, :]

        if self.nodata is not None:
            nodata_val = (
                self.data.dtype.type(self.nodata)
                if np.issubdtype(self.data.dtype, np.integer)
                else self.nodata
            )
            if np.isnan(nodata_val) if isinstance(nodata_val, float) else False:
                out_of_bounds |= np.isnan(sampled.astype(np.float64))
            else:
                out_of_bounds |= (sampled == nodata_val)

        if advanced:
            safe_sampled = np.where(
                (sampled >= 0) & (sampled < 256),
                sampled.astype(np.int32),
                0,
            )
            cat_idx_arr = _WORLDCOVER_TO_ADVANCED_IDX[safe_sampled]
            cat_idx_arr = np.where(out_of_bounds, 0, cat_idx_arr)
            result = np.empty(cat_idx_arr.shape, dtype=object)
            result[:] = _ADVANCED_CATEGORIES[0]
            for i, cat_name in enumerate(_ADVANCED_CATEGORIES):
                result[cat_idx_arr == i] = cat_name
            if rx_override:
                result[:, :] = _legacy_to_advanced_override(rx_override)
            return result

        valid_class = (sampled >= 0) & (sampled < 256)
        safe_sampled = np.where(valid_class, sampled, 0).astype(np.int32, copy=False)
        cat_idx = _WORLDCOVER_TO_CATEGORY[safe_sampled]
        cat_idx = np.where(out_of_bounds, 0, cat_idx)
        if rx_override:
            cat_idx[:] = _CATEGORY_IDX.get(rx_override, 0)
        return _CLUTTER_LOSS_ARRAY[cat_idx]