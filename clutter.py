# -*- coding: utf-8 -*-
"""Terminal clutter correction helpers for NoWires."""

import logging
from dataclasses import dataclass

import numpy as np
from osgeo import gdal

logger = logging.getLogger(__name__)


CLUTTER_CATEGORIES = ("open", "rural", "vegetation", "suburban", "urban")
CLUTTER_LOSS_DB = {
    "open": 0.0,
    "rural": 2.0,
    "vegetation": 6.0,
    "suburban": 8.0,
    "urban": 10.0,
}
CLUTTER_MODEL_OPTIONS = ["Off", "Simple clutter correction"]
CLUTTER_OVERRIDE_OPTIONS = ["Auto", "open", "rural", "vegetation", "suburban", "urban"]


@dataclass(frozen=True)
class TerminalClutterLosses:
    tx_category: str
    rx_category: str
    tx_loss_db: float
    rx_loss_db: float
    total_loss_db: float
    source: str


def worldcover_class_to_clutter_category(class_id):
    value = int(class_id)
    if value in (10, 95, 100):
        return "vegetation"
    if value in (20, 30, 40):
        return "rural"
    if value == 50:
        return "urban"
    if value == 60:
        return "open"
    if value in (70, 80, 90):
        return "open"
    return "open"


def clutter_loss_db(category, frequency_mhz):
    del frequency_mhz
    return CLUTTER_LOSS_DB.get(category, 0.0)


def clutter_override_value(index_or_category):
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
):
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


@dataclass
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
                min_lat, max_lat = max_lat, min_lat
            return cls(data, min_lat, max_lat, min_lon, max_lon, nodata, str(path))
        finally:
            ds = None

    def sample_class(self, lat, lon):
        if lat < self.min_lat or lat > self.max_lat:
            return None
        if lon < self.min_lon or lon > self.max_lon:
            return None
        n_rows, n_cols = self.data.shape
        d_lat = (self.max_lat - self.min_lat) / max(n_rows - 1, 1)
        d_lon = (self.max_lon - self.min_lon) / max(n_cols - 1, 1)
        y = int(round((self.max_lat - lat) / d_lat))
        x = int(round((lon - self.min_lon) / d_lon))
        y = max(0, min(n_rows - 1, y))
        x = max(0, min(n_cols - 1, x))
        value = self.data[y, x]
        if self.nodata is not None and value == self.nodata:
            return None
        return int(value)

    def sample_category(self, lat, lon):
        class_id = self.sample_class(lat, lon)
        if class_id is None:
            return None
        return worldcover_class_to_clutter_category(class_id)


def ensure_clutter_grid_for_area(south, north, west, east, feedback=None):
    try:
        from .worldcover_downloader import ensure_worldcover_for_area
    except ImportError:
        from worldcover_downloader import ensure_worldcover_for_area

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
):
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
