# -*- coding: utf-8 -*-
"""ESA WorldCover 2020 v100 tile download, caching, and merging.

Downloads Cloud-Optimized GeoTIFF tiles from the ESA WorldCover AWS
Open Data bucket on demand, caches them locally, and provides
utilities to clip/merge for a given area of interest.
"""

import logging
import math
import os
import re
import ssl
import tempfile
import time
import urllib.error
import urllib.request

from osgeo import gdal, ogr, osr

logger = logging.getLogger(__name__)

WORLDCOVER_BASE_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
    "/v100/2020/map/"
)
WORLDCOVER_TILE_SIZE_DEG = 3
_DOWNLOAD_RETRIES = 3
_MAX_TILES = 200
_VALID_TILE_RE = re.compile(r"^[NS]\d{2}[EW]\d{3}$")


def get_worldcover_dir():
    worldcover_dir = os.path.join(tempfile.gettempdir(), "NoWires", "worldcover")
    os.makedirs(worldcover_dir, mode=0o700, exist_ok=True)
    return worldcover_dir


def worldcover_tile_id(lat, lon):
    snapped_lat = math.floor(lat / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG
    snapped_lon = math.floor(lon / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG
    ns = "N" if snapped_lat >= 0 else "S"
    ew = "E" if snapped_lon >= 0 else "W"
    return "{}{:02d}{}{:03d}".format(ns, abs(snapped_lat), ew, abs(snapped_lon))


def worldcover_tile_filename(tile_id):
    return "ESA_WorldCover_10m_2020_v100_{}_Map.tif".format(tile_id)


def worldcover_tile_url(tile_id):
    return "{}{}".format(WORLDCOVER_BASE_URL, worldcover_tile_filename(tile_id))


def required_worldcover_tiles(south, north, west, east, max_tiles=_MAX_TILES):
    tiles = []
    for lat in range(
        math.floor(south / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
        math.ceil(north / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
        WORLDCOVER_TILE_SIZE_DEG,
    ):
        for lon in range(
            math.floor(west / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
            math.ceil(east / WORLDCOVER_TILE_SIZE_DEG) * WORLDCOVER_TILE_SIZE_DEG,
            WORLDCOVER_TILE_SIZE_DEG,
        ):
            tile_id = worldcover_tile_id(lat, lon)
            if tile_id not in tiles:
                tiles.append(tile_id)

    if len(tiles) > max_tiles:
        raise ValueError(
            "Area requires {} WorldCover tiles (max {}). "
            "Reduce the analysis area.".format(len(tiles), max_tiles)
        )
    return tiles


def download_worldcover_tiles(tile_list, temp_dir=None, feedback=None):
    if temp_dir is None:
        temp_dir = get_worldcover_dir()

    ctx = ssl.create_default_context()
    default_opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
    available = []

    for tile_id in tile_list:
        if not _VALID_TILE_RE.match(tile_id):
            logger.error("Invalid WorldCover tile ID rejected: %s", tile_id)
            continue

        filename = worldcover_tile_filename(tile_id)
        local_tif = os.path.join(temp_dir, filename)

        if os.path.exists(local_tif):
            logger.debug("WorldCover cache hit: %s", tile_id)
            if feedback:
                feedback.pushInfo("WorldCover cache hit: " + tile_id)
            available.append(local_tif)
            continue

        tile_url = worldcover_tile_url(tile_id)
        if feedback:
            feedback.pushInfo("Downloading WorldCover: " + tile_url)

        opener = default_opener
        downloaded = False

        for attempt in range(_DOWNLOAD_RETRIES):
            try:
                with opener.open(tile_url, timeout=120) as response:
                    expected_size = int(response.headers.get("Content-Length", 0))
                    bytes_received = 0
                    tmp_path = local_tif + ".tmp"
                    with open(tmp_path, "wb") as f:
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            bytes_received += len(chunk)

                if expected_size > 0 and bytes_received != expected_size:
                    logger.warning(
                        "Incomplete WorldCover download %s: %d/%d bytes",
                        tile_id,
                        bytes_received,
                        expected_size,
                    )
                    try:
                        os.unlink(local_tif + ".tmp")
                    except OSError:
                        pass
                    if attempt < _DOWNLOAD_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise ValueError(
                        "Incomplete WorldCover download: {} of {} bytes".format(
                            bytes_received, expected_size
                        )
                    )

                test_ds = gdal.Open(local_tif + ".tmp")
                if test_ds is None:
                    logger.warning("Downloaded WorldCover tile is corrupt: %s", tile_id)
                    try:
                        os.unlink(local_tif + ".tmp")
                    except OSError:
                        pass
                    if attempt < _DOWNLOAD_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                test_ds = None

                os.rename(local_tif + ".tmp", local_tif)
                available.append(local_tif)
                downloaded = True
                break

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.info("WorldCover tile not available (404): %s", tile_id)
                    if feedback:
                        feedback.pushInfo(
                            "WorldCover tile not available (HTTP 404): " + tile_id
                        )
                    break
                else:
                    logger.warning(
                        "HTTP %d downloading %s (attempt %d/%d): %s",
                        e.code,
                        tile_id,
                        attempt + 1,
                        _DOWNLOAD_RETRIES,
                        e,
                    )
                    if attempt < _DOWNLOAD_RETRIES - 1:
                        time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(
                    "Error downloading %s (attempt %d/%d): %s",
                    tile_id,
                    attempt + 1,
                    _DOWNLOAD_RETRIES,
                    e,
                )
                if feedback:
                    feedback.pushInfo(
                        "Error downloading {} (attempt {}): {}".format(
                            tile_id, attempt + 1, str(e)
                        )
                    )
                if attempt < _DOWNLOAD_RETRIES - 1:
                    time.sleep(2 ** attempt)

        if not downloaded and not os.path.exists(local_tif):
            pass

    return available


def clip_and_merge_worldcover(tile_paths, south, north, west, east, temp_dir=None, feedback=None):
    if temp_dir is None:
        temp_dir = get_worldcover_dir()

    if not tile_paths:
        return None

    aoi_shp = os.path.join(temp_dir, "worldcover_aoi_clip.shp")
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(aoi_shp):
        shp_driver.DeleteDataSource(aoi_shp)

    ds = shp_driver.CreateDataSource(aoi_shp)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = ds.CreateLayer("aoi", srs=srs, geom_type=ogr.wkbPolygon)
    feat_defn = layer.GetLayerDefn()
    feature = ogr.Feature(feat_defn)

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(west, south)
    ring.AddPoint(east, south)
    ring.AddPoint(east, north)
    ring.AddPoint(west, north)
    ring.AddPoint(west, south)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    feature.SetGeometry(poly)
    layer.CreateFeature(feature)
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
            dstNodata=0,
            srcSRS="EPSG:4326",
            dstSRS="EPSG:4326",
            format="GTiff",
            creationOptions=["COMPRESS=LZW", "TILED=YES"],
        )
        if result is None:
            logger.warning("Warp failed for %s", os.path.basename(path))
            continue

        check = gdal.Open(clip_path)
        if check is None:
            logger.warning("Empty clip result for %s", os.path.basename(path))
            continue
        check = None
        clipped.append(clip_path)

    if not clipped:
        return None

    if len(clipped) == 1:
        return clipped[0]

    merged_path = os.path.join(temp_dir, "merged_worldcover.tif")
    if feedback:
        feedback.pushInfo("Merging {} clipped WorldCover tiles".format(len(clipped)))

    result = gdal.Warp(
        merged_path,
        clipped,
        dstNodata=0,
        format="GTiff",
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )
    if result is None:
        logger.error("WorldCover merge Warp failed")
        return None

    return merged_path


def ensure_worldcover_for_area(south, north, west, east, feedback=None):
    temp_dir = get_worldcover_dir()

    if feedback:
        feedback.pushInfo("Calculating required WorldCover tiles")

    tiles = required_worldcover_tiles(south, north, west, east)
    if not tiles:
        if feedback:
            feedback.pushInfo("No WorldCover tiles found for the given area.")
        return None

    if feedback:
        feedback.pushInfo("Downloading WorldCover tiles")

    tile_paths = download_worldcover_tiles(
        tiles, temp_dir=temp_dir, feedback=feedback
    )

    if not tile_paths:
        if feedback:
            feedback.pushInfo("No WorldCover tiles were downloaded successfully.")
        return None

    if len(tile_paths) == 1:
        return tile_paths[0]

    if feedback:
        feedback.pushInfo("Clipping and merging WorldCover tiles")

    return clip_and_merge_worldcover(
        tile_paths,
        south,
        north,
        west,
        east,
        temp_dir=temp_dir,
        feedback=feedback,
    )