#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Package repeater coverage into a portable GeoPackage (.gpkg) with raster, vectors, and style."""
import os
import math
from osgeo import gdal, ogr, osr
from NoWires.constants import EARTH_RADIUS_M, GDAL_DRIVER_NAME

gdal.UseExceptions()
ogr.UseExceptions()


def _plugin_version() -> str:
    """Read the plugin version from metadata.txt (single source of truth)."""
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "metadata.txt")
    with open(metadata_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("version="):
                return line.split("=", 1)[1].strip()
    return "0.0.0"

TIF = "/output/7800h_repeater_90-50-50_1024.tif"
CSV = "/output/7800h_repeater_90-50-50_1024.csv"
GPKG = "/output/7800h_repeater_90-50-50.gpkg"

WGS84 = osr.SpatialReference()
WGS84.ImportFromEPSG(4326)

TX_LON, TX_LAT = 125.66039, 7.154183
RADIUS_KM = 50.0
SENSITIVITY = -116.0

if os.path.exists(GPKG):
    os.remove(GPKG)

# ── 1. Convert coverage GeoTIFF → GPKG raster (Byte tiles with scale/offset) ──
# The raster is Float32 dBm.  Rescale to 0-250 Byte for PNG tiles.
# Leave 251-255 reserved: 251=no_data, 252=water/invalid.
# Scale: prx values roughly -250..0 dBm. byte = prx / 2 + 125 (so -250→0, 0→125)
# Then the user can load it as pseudocolor with the embedded style.

src_ds = gdal.Open(TIF)
src_band = src_ds.GetRasterBand(1)
arr = src_band.ReadAsArray()
nodata_raw = src_band.GetNoDataValue()

# Scale: byte = (prx_dbm + 250.0) / 2.0  → -250→0, -100→75, 0→125
valid = (arr != nodata_raw)
prx_min = arr[valid].min()
prx_max = arr[valid].max()
byte_arr = ((arr - prx_min) * (250.0 / (prx_max - prx_min))).clip(0, 250).astype('uint8')
byte_nodata = 255
byte_arr[~valid] = byte_nodata
print(f"  Raster: prx {prx_min:.0f}..{prx_max:.0f} dBm → Byte 0..250, nodata={byte_nodata}")

tmp_tif = "/tmp/scaled_byte.tif"
tmp_ds = gdal.GetDriverByName(GDAL_DRIVER_NAME).Create(tmp_tif, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte)
tmp_ds.SetGeoTransform(src_ds.GetGeoTransform())
tmp_ds.SetProjection(src_ds.GetProjection())
tmp_band = tmp_ds.GetRasterBand(1)
tmp_band.WriteArray(byte_arr)
tmp_band.SetNoDataValue(byte_nodata)
tmp_band.ComputeStatistics(False)
tmp_band.SetScale(float(prx_max - prx_min) / 250.0)
tmp_band.SetOffset(float(prx_min))
tmp_ds.FlushCache()
tmp_ds = None
src_ds = None

# Convert to GPKG with PNG tiles
opts = gdal.TranslateOptions(
    format="GPKG",
    outputType=gdal.GDT_Byte,
    creationOptions=[
        "RASTER_TABLE=coverage_prx",
        "TILE_FORMAT=PNG",
        "APPEND_SUBDATASET=NO",
    ],
)
gdal.Translate(GPKG, tmp_tif, options=opts)
os.remove(tmp_tif)
print("  Raster layer 'coverage_prx' written to GPKG")

# ── 2. Add TX site point layer ──
gpkg_ds = ogr.Open(GPKG, update=1)
tx_layer = gpkg_ds.CreateLayer("tx_site", WGS84, ogr.wkbPoint)
tx_layer.CreateField(ogr.FieldDefn("name", ogr.OFTString))
tx_layer.CreateField(ogr.FieldDefn("frequency", ogr.OFTReal))
tx_layer.CreateField(ogr.FieldDefn("power_w", ogr.OFTReal))
tx_layer.CreateField(ogr.FieldDefn("height_m", ogr.OFTReal))
tx_layer.CreateField(ogr.FieldDefn("antenna", ogr.OFTString))
feat = ogr.Feature(tx_layer.GetLayerDefn())
feat.SetField("name", "RF-7800V-HH Repeater")
feat.SetField("frequency", 47.0)
feat.SetField("power_w", 10.0)
feat.SetField("height_m", 30.0)
feat.SetField("antenna", "4 dBi VHF dipole, 1.5 dB coax")
pt = ogr.Geometry(ogr.wkbPoint)
pt.AddPoint(TX_LON, TX_LAT)
feat.SetGeometry(pt)
tx_layer.CreateFeature(feat)
feat = None
print("  Vector layer 'tx_site' written")

# ── 3. Add 50 km coverage boundary circle ──
boundary = gpkg_ds.CreateLayer("coverage_boundary", WGS84, ogr.wkbPolygon)
boundary.CreateField(ogr.FieldDefn("radius_km", ogr.OFTReal))
earth_r = EARTH_RADIUS_M
circle_pts = []
n_seg = 360
for i in range(n_seg + 1):
    bearing = math.radians(float(i) * 360.0 / n_seg)
    arc = RADIUS_KM * 1000.0 / earth_r
    lat_r = math.asin(
        math.sin(math.radians(TX_LAT)) * math.cos(arc) +
        math.cos(math.radians(TX_LAT)) * math.sin(arc) * math.cos(bearing)
    )
    lon_r = math.radians(TX_LON) + math.atan2(
        math.sin(bearing) * math.sin(arc) * math.cos(math.radians(TX_LAT)),
        math.cos(arc) - math.sin(math.radians(TX_LAT)) * math.sin(lat_r)
    )
    circle_pts.append((math.degrees(lon_r), math.degrees(lat_r)))

ring = ogr.Geometry(ogr.wkbLinearRing)
for lon, lat in circle_pts:
    ring.AddPoint(lon, lat)
ring.CloseRings()
poly = ogr.Geometry(ogr.wkbPolygon)
poly.AddGeometry(ring)
feat = ogr.Feature(boundary.GetLayerDefn())
feat.SetField("radius_km", RADIUS_KM)
feat.SetGeometry(poly)
boundary.CreateFeature(feat)
feat = None
print("  Vector layer 'coverage_boundary' written")

# ── 4. Parse CSV and embed metadata ──
meta = {}
with open(CSV) as f:
    for line in f:
        parts = line.strip().split(",", 2)
        if len(parts) >= 3:
            section, key, value = parts
            if section == "results":
                meta[key] = value
pct_above = float(meta.get("pct_above_sensitivity", 0))
mean_prx = float(meta.get("mean_prx_dbm", 0))
avg_dist = float(meta.get("average_distance_km", 0))
reliability = meta.get("reliability_summary", "")

gpkg_ds.SetMetadata([
    f"GENERATOR=NoWires QGIS Plugin v{_plugin_version()}",
    "RADIO=L3Harris RF-7800V-HH",
    "MODE=Repeater (fixed site)",
    "FREQUENCY_MHZ=47.0",
    "TX_POWER=10 W (40 dBm) + 4 dBi ant - 1.5 dB coax = 42.5 dBm EIRP",
    "TX_HEIGHT=30 m AGL",
    "RX_HEIGHT=1.5 m (handheld)",
    "RX_SENSITIVITY=-116 dBm (FM 12 dB SINAD)",
    "CLUTTER=SIMPLE (per-category fixed losses)",
    "TIME_PCT=90.0",
    "LOCATION_PCT=50.0",
    "SITUATION_PCT=50.0",
    f"COVERAGE_ABOVE_SENSITIVITY={pct_above:.1f}%",
    f"MEAN_PRX={mean_prx:.1f} dBm",
    f"AVG_USABLE_DISTANCE={avg_dist:.1f} km",
    f"RELIABILITY={reliability}",
    "GRID_SIZE=1024 x 1024 (98m x 98m pixels)",
    "DEM_SOURCE=Copernicus GLO-30 (30m)",
    "CLUTTER_SOURCE=ESA WorldCover 2020 v100 (10m)",
    "CLIMATE=Equatorial",
    "COVERAGE_RADIUS=50 km",
    "SITE=7.1542 N, 125.6604 E (Philippines)",
], "coverage_metadata")

# metadata table with structured key-value
for k, v in meta.items():
    gpkg_ds.SetMetadataItem(f"RESULT_{k}", v, "coverage_metadata")

gpkg_ds = None
print("  Metadata written")

sz = os.path.getsize(GPKG)
print(f"\n  {GPKG}")
print(f"  Size: {sz / 1048576:.1f} MB")
print("  Layers: coverage_prx (raster), tx_site (point), coverage_boundary (polygon)")
print("  Metadata table: coverage_metadata")
print("\n  To view: Layer → Add Layer → Add Raster/Vector Layer → select .gpkg")
print("  Or: drag .gpkg into QGIS, all 3 layers will appear in the browser.")
