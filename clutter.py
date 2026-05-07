# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                      A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                              -------------------
         begin                : 2026-04-22
         copyright            : (C) 2026 Bortre Tenamo
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


Terminal clutter correction helpers for NoWires.
"""

import logging
from dataclasses import dataclass

import numpy as np
from osgeo import gdal

from .worldcover_downloader import ensure_worldcover_for_area

logger = logging.getLogger(__name__)

LEGACY_CLUTTER_CATEGORIES = ("open", "rural", "vegetation", "suburban", "urban")
CLUTTER_CATEGORIES = LEGACY_CLUTTER_CATEGORIES
CLUTTER_LOSS_DB = {
    "open": 0.0,
    "rural": 2.0,
    "vegetation": 6.0,
    "suburban": 8.0,
    "urban": 10.0,
}
CLUTTER_MODEL_OPTIONS = [
    "Off",
    "Simple clutter correction",
    "Advanced clutter correction",
]
CLUTTER_OVERRIDE_OPTIONS = [
    "Auto",
    "open", "rural", "vegetation", "suburban", "urban",
    "open_rural", "dense_rural",
]

_CATEGORY_IDX = {k: i for i, k in enumerate(CLUTTER_CATEGORIES)}
_CLUTTER_LOSS_ARRAY = np.array([
    CLUTTER_LOSS_DB["open"],
    CLUTTER_LOSS_DB["rural"],
    CLUTTER_LOSS_DB["vegetation"],
    CLUTTER_LOSS_DB["suburban"],
    CLUTTER_LOSS_DB["urban"],
], dtype=np.float64)

# Lookup table: ESA WorldCover class ID (0-255) -> clutter category index (0-4)
# Unknown classes default to 0 (open)
_WORLDCOVER_TO_CATEGORY = np.zeros(256, dtype=np.int32)
_WORLDCOVER_TO_CATEGORY[10] = 2
_WORLDCOVER_TO_CATEGORY[20] = 2
_WORLDCOVER_TO_CATEGORY[95] = 2
_WORLDCOVER_TO_CATEGORY[100] = 2
_WORLDCOVER_TO_CATEGORY[30] = 1
_WORLDCOVER_TO_CATEGORY[40] = 1
_WORLDCOVER_TO_CATEGORY[50] = 4
_WORLDCOVER_TO_CATEGORY[60] = 0
_WORLDCOVER_TO_CATEGORY[70] = 0
_WORLDCOVER_TO_CATEGORY[80] = 0
_WORLDCOVER_TO_CATEGORY[90] = 0


def worldcover_class_to_clutter_category(class_id) -> str:
    raw = int(class_id)
    if raw < 0 or raw > 255:
        logger.warning("Unexpected WorldCover class ID %d (outside 0-255 range)", raw)
    return CLUTTER_CATEGORIES[_WORLDCOVER_TO_CATEGORY[raw % 256]]


def clutter_loss_db(category, frequency_mhz) -> float:
    """Return excess clutter loss for a given category.

    Currently frequency-independent. A future version may apply
    frequency-dependent corrections per ITU-R P.1812.
    """
    del frequency_mhz
    return CLUTTER_LOSS_DB.get(category, 0.0)


def clutter_override_value(index_or_category) -> str | None:
    if index_or_category is None:
        return None
    if isinstance(index_or_category, str):
        return None if index_or_category == "Auto" else index_or_category
    idx = int(index_or_category)
    if idx <= 0 or idx >= len(CLUTTER_OVERRIDE_OPTIONS):
        return None
    return CLUTTER_OVERRIDE_OPTIONS[idx]


def clutter_source_label(
    enabled,
    land_cover_grid=None,
    raster_path=None,
    tx_override=None,
    rx_override=None,
) -> str:
    """Return a user-visible source label for clutter reports."""
    if not enabled:
        return "off"
    sources = []
    if tx_override or rx_override:
        sources.append("override")
    if raster_path:
        sources.append(str(raster_path))
    elif land_cover_grid is not None:
        sources.append(land_cover_grid.source)
    if sources:
        return ",".join(sources)
    return "fallback_open"


@dataclass(frozen=True)
class TerminalClutterLosses:
    tx_category: str
    rx_category: str
    tx_loss_db: float
    rx_loss_db: float
    total_loss_db: float
    source: str


@dataclass(slots=True)
class LandCoverGrid:
    data: np.ndarray
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    nodata: float | None
    source: str

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

    def sample_class(self, lat, lon) -> int | None:
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
        return worldcover_class_to_clutter_category(class_id)

    def sample_category_grid(self, lats, lons, rx_override=None):
        """Vectorized category sampling for a 2D grid of lats/lons.

        Returns a 2D array of clutter loss values in dB, shape (len(lats), len(lons)).
        """
        n = len(lats)
        m = len(lons)
        if self.data is None:
            default = _CLUTTER_LOSS_ARRAY[0] if rx_override else 0.0
            return np.full((n, m), default, dtype=np.float64)
        n_rows, n_cols = self.data.shape
        d_lat = (self.max_lat - self.min_lat) / n_rows
        d_lon = (self.max_lon - self.min_lon) / n_cols
        lat_arr = np.asarray(lats, dtype=np.float64)
        lon_arr = np.asarray(lons, dtype=np.float64)
        y_idx = np.clip(((self.max_lat - lat_arr) / d_lat).astype(np.int32), 0, n_rows - 1)
        x_idx = np.clip(((lon_arr - self.min_lon) / d_lon).astype(np.int32), 0, n_cols - 1)
        sampled = self.data[y_idx[:, np.newaxis], x_idx[np.newaxis, :]]
        cat_idx = _WORLDCOVER_TO_CATEGORY[sampled]
        lat_oob = (lat_arr < self.min_lat) | (lat_arr > self.max_lat)
        lon_oob = (lon_arr < self.min_lon) | (lon_arr > self.max_lon)
        out_of_bounds = lat_oob[:, np.newaxis] | lon_oob[np.newaxis, :]
        if self.nodata is not None:
            nodata_val = self.data.dtype.type(self.nodata) if np.issubdtype(self.data.dtype, np.integer) else self.nodata
            if np.isnan(nodata_val):
                out_of_bounds |= np.isnan(sampled.astype(np.float64))
            else:
                out_of_bounds |= (sampled == nodata_val)
        cat_idx = np.where(out_of_bounds, 0, cat_idx)
        if rx_override:
            override_idx = _CATEGORY_IDX.get(rx_override, 0)
            cat_idx[:] = override_idx
        return _CLUTTER_LOSS_ARRAY[cat_idx]


def ensure_clutter_grid_for_area(south, north, west, east, feedback=None) -> LandCoverGrid | None:
    raster_path = ensure_worldcover_for_area(south, north, west, east, feedback=feedback)
    if raster_path is None:
        return None
    try:
        return LandCoverGrid.from_raster(raster_path)
    except RuntimeError:
        logger.warning("Failed to load downloaded WorldCover raster")
        return None


def _resolve_category(lat, lon, override, land_cover_grid):
    if override:
        return override, "override"
    if land_cover_grid is not None:
        category = land_cover_grid.sample_category(lat, lon)
        if category is not None:
            return category, land_cover_grid.source
    return "open", "fallback_open"


def compute_terminal_clutter_losses(
    tx_lat,
    tx_lon,
    rx_lat,
    rx_lon,
    frequency_mhz,
    enabled=False,
    land_cover_grid=None,
    tx_override=None,
    rx_override=None,
) -> TerminalClutterLosses:
    if not enabled:
        return TerminalClutterLosses("open", "open", 0.0, 0.0, 0.0, "off")

    tx_category, tx_source = _resolve_category(
        tx_lat, tx_lon, tx_override, land_cover_grid
    )
    rx_category, rx_source = _resolve_category(
        rx_lat, rx_lon, rx_override, land_cover_grid
    )
    tx_loss = clutter_loss_db(tx_category, frequency_mhz)
    rx_loss = clutter_loss_db(rx_category, frequency_mhz)
    source = tx_source if tx_source == rx_source else "{},{}".format(tx_source, rx_source)
    return TerminalClutterLosses(
        tx_category=tx_category,
        rx_category=rx_category,
        tx_loss_db=tx_loss,
        rx_loss_db=rx_loss,
        total_loss_db=tx_loss + rx_loss,
        source=source,
    )