#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Terrain audit — elevation variation per quadrant from DEM tiles."""
import glob
import os

# Quick check: what DEM tiles were cached?
cache = "/tmp/NoWires-root"
print("=== CACHED DEM TILES ===")
for f in sorted(glob.glob(os.path.join(cache, "*.tif"))):
    sz_mb = os.path.getsize(f) / (1024*1024)
    print(f"  {os.path.basename(f):<55s} {sz_mb:>6.1f} MB")

print(f"\n  Total cache: {sum(os.path.getsize(f) for f in glob.glob(os.path.join(cache, '**/*.tif'), recursive=True)) / (1024*1024):.1f} MB")
