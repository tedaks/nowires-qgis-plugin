#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export portable QGIS project (.qgz), style (.qml), and layer definition (.qlr)
for the repeater 90/50/50 coverage, all with relative paths (drop-and-open on any machine)."""
import os
import sys
import zipfile
import shutil

from qgis.core import (
    QgsApplication, QgsProject, QgsRasterLayer, QgsMapLayer,
    QgsReferencedRectangle,
)
from NoWires.radio_coverage.palette import apply_coverage_style

OUT = "/output/portable"
os.makedirs(OUT, exist_ok=True)
TIF_SRC = "/output/7800h_repeater_90-50-50_1024.tif"
TIF_NAME = "repeater_coverage_90-50-50.tif"

# Copy raster into the portable directory
shutil.copy2(TIF_SRC, os.path.join(OUT, TIF_NAME))
# Copy reports
for ext in (".csv", ".json", ".html"):
    src = TIF_SRC.replace(".tif", ext)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(OUT, os.path.basename(src)))

app = QgsApplication([], False)
app.initQgis()

project = QgsProject.instance()

# ── Add raster layer with NoWires coverage style ──
raster = QgsRasterLayer(os.path.join(OUT, TIF_NAME), "Coverage — 7800H Repeater 90/50/50")
if not raster.isValid():
    print("ERROR: raster invalid")
    app.exitQgis()
    sys.exit(1)

apply_coverage_style(raster)
project.addMapLayer(raster)

# ── Set view extent to raster bounds (fixes white screen on open) ──
ext = raster.extent()
ref_ext = QgsReferencedRectangle(ext, raster.crs())
project.viewSettings().setDefaultViewExtent(ref_ext)
project.viewSettings().setPresetFullExtent(ref_ext)

# ── Set relative paths in the project ──
project.writeEntry("Paths", "/Absolute", False)

# ── Save .qgs first, then repack as .qgz ──
qgs_path = os.path.join(OUT, "repeater_coverage_90-50-50.qgs")
qgz_path = os.path.join(OUT, "repeater_coverage_90-50-50.qgz")

if not project.write(qgs_path):
    print("ERROR: project.write() returned False")
else:
    with zipfile.ZipFile(qgz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(qgs_path, os.path.basename(qgs_path))
    os.remove(qgs_path)
    print(f"  Project: {qgz_path}")

# ── Export .qml style file ──
qml_path = os.path.join(OUT, "nowires_coverage_style.qml")
result = raster.saveNamedStyle(qml_path, QgsMapLayer.StyleCategory.AllStyleCategories)
if isinstance(result, tuple):
    ok = result[1]
else:
    ok = (result == QgsMapLayer.SaveStyleResult.Success)
if ok and os.path.exists(qml_path):
    print(f"  Style:   {qml_path}")
else:
    print(f"  Style:   saveNamedStyle returned {result}. Falling back to doc export...")
    doc = raster.exportNamedStyle()
    if doc:
        content = doc.toString()
        with open(qml_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Style:   {qml_path} ({len(content)} bytes)" if os.path.exists(qml_path) else "  Style:   write failed")
    else:
        print("  Style:   exportNamedStyle returned None")

app.exitQgis()

print(f"\n  Portable directory: {OUT}")
# Clean up temp files
for tmp in [f for f in os.listdir(OUT) if f.endswith("~")]:
    os.remove(os.path.join(OUT, tmp))
for fname in sorted(os.listdir(OUT)):
    sz = os.path.getsize(os.path.join(OUT, fname))
    print(f"    {fname:<50s} {sz:>8d} bytes")
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print(f"    {'TOTAL':<50s} {total:>8d} bytes ({total/1048576:.1f} MB)")
print("\n  Drop the .qgz file into QGIS to see the styled coverage layer.")
print("  Or drag the .tif in and load the .qml style to apply the heatmap.")
