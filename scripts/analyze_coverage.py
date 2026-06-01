#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Spatial analysis of NoWires coverage GeoTIFF."""
import numpy as np
from osgeo import gdal
gdal.UseExceptions()

ds = gdal.Open("/output/7800h_47mhz_10w_30m_advclutter_1024.tif")
band = ds.GetRasterBand(1)
arr = band.ReadAsArray()
gt = ds.GetGeoTransform()
nodata = band.GetNoDataValue()

valid = arr != nodata if nodata is not None else np.ones_like(arr, dtype=bool)
valid_arr = arr[valid]
total_valid = valid.sum()

sensitivity = -116.0
above_n = (valid_arr >= sensitivity).sum()
below_n = total_valid - above_n

pct_pts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
pct_vals = np.percentile(valid_arr, pct_pts)

tx_lon, tx_lat = 125.66039, 7.154183
cols, rows = np.meshgrid(np.arange(1024), np.arange(1024))
lon = gt[0] + cols * gt[1] + rows * gt[2]
lat = gt[3] + cols * gt[4] + rows * gt[5]

dlon = np.radians(lon - tx_lon)
dlat = np.radians(lat - tx_lat)
a = np.sin(dlat/2)**2 + np.cos(np.radians(tx_lat)) * np.cos(np.radians(lat)) * np.sin(dlon/2)**2
c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
dist_km = 6371.0 * c

print("=" * 72)
print("  NoWires Coverage Analysis — RF-7800V-HH @ 47 MHz / 10 W / 30 m AGL")
print("=" * 72)

print("\n=== COVERAGE BY DISTANCE RING ===")
print(f"  {'Ring (km)':<14} {'Valid':>7}  {'>sensitivity':>12}  {'Pct':>6}  {'Mean Prx':>9}  {'Median Prx':>10}  {'Min Prx':>9}")
rings = [(0,5),(5,10),(10,15),(15,20),(20,25),(25,30),(30,35),(35,40),(40,45),(45,50)]
for r0, r1 in rings:
    mask = (dist_km >= r0) & (dist_km < r1) & valid
    n = mask.sum()
    if n > 0:
        a_n = int((arr[mask] >= sensitivity).sum())
        mean_v = arr[mask].mean()
        med_v = np.median(arr[mask])
        min_v = arr[mask].min()
        pct_v = 100 * a_n / n
        print(f"  {r0:>3}-{r1:<3} km      {n:>7}  {a_n:>12}  {pct_v:>5.1f}%  {mean_v:>9.1f}  {med_v:>10.1f}  {min_v:>9.1f}")

print("\n=== SIGNAL STRENGTH DISTRIBUTION (valid pixels) ===")
bins = [(-999, -130), (-130, -120), (-120, -116), (-116, -110), (-110, -100),
        (-100, -90), (-90, -80), (-80, -60), (-60, 0)]
for lo, hi in bins:
    if lo < -900:
        n = int((valid_arr <= hi).sum())
    else:
        n = int(((valid_arr > lo) & (valid_arr <= hi)).sum())
    pct_s = 100 * n / total_valid
    bar = "#" * int(pct_s)
    label = f"{lo} .. {hi}" if lo > -900 else f"   <= {hi}"
    print(f"  {label:>16} dBm: {n:>7} ({pct_s:>5.1f}%) {bar}")

bearing = np.degrees(np.arctan2(dlon, dlat))
north = (bearing > -45) & (bearing <= 45) & valid
east  = (bearing > 45) & (bearing <= 135) & valid
south = ((bearing > 135) | (bearing <= -135)) & valid
west  = (bearing > -135) & (bearing <= -45) & valid
print("\n=== DIRECTIONAL COVERAGE (above -116 dBm) ===")
for name, mask in [("North", north), ("East", east), ("South", south), ("West", west)]:
    n = mask.sum()
    a_n = int((arr[mask] >= sensitivity).sum())
    if n > 0:
        print(f"  {name:>6}: {a_n:>6}/{n:<6} ({100*a_n/n:>5.1f}%)  mean={arr[mask].mean():.1f} dBm  max={arr[mask].max():.1f} dBm")

print("\n=== PERCENTILE TABLE (valid Prx dBm) ===")
for p, v in zip(pct_pts, pct_vals):
    print(f"  P{p:>2d}:  {v:>8.1f} dBm")

print("\n=== SUMMARY ===")
print(f"  Valid pixels:       {total_valid} / {arr.size} ({100*total_valid/arr.size:.1f}%)")
print(f"  Pixels > -116 dBm:  {int(above_n)} ({100*above_n/total_valid:.1f}% of valid)")
print(f"  Mean Prx:           {valid_arr.mean():.1f} dBm")
print(f"  Median Prx:         {np.median(valid_arr):.1f} dBm")
print(f"  Std Dev:            {valid_arr.std():.1f} dB")
print(f"  Min Prx:            {valid_arr.min():.1f} dBm")
print(f"  Max Prx:            {valid_arr.max():.1f} dBm")
print(f"  IQR:                {pct_vals[5]:.1f} to {pct_vals[3]:.1f} dBm (spread: {pct_vals[5]-pct_vals[3]:.1f} dB)")

# Terrain/elevation context
print("\n=== GRID GEOMETRY ===")
print(f"  Top-left:  {lat.max():.4f} N, {lon.min():.4f} E")
print(f"  Bottom-right: {lat.min():.4f} N, {lon.max():.4f} E")
print(f"  Pixel size: {abs(gt[1]):.6f} deg lon x {abs(gt[5]):.6f} deg lat")
print(f"  Pixel size (approx): {abs(gt[1]) * 111320:.1f} m x {abs(gt[5]) * 111320:.1f} m")
print(f"  TX location: {tx_lat:.4f} N, {tx_lon:.4f} E")

ds = None
