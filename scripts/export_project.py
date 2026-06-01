#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export QGIS project + style for portable reuse of repeater coverage layer."""
import os
import sys
import shutil
import zipfile

from qgis.core import (
    QgsApplication, QgsProject, QgsRasterLayer, QgsMapLayer,
)
from NoWires.radio_coverage.palette import apply_coverage_style

TIF = "/output/7800h_repeater_90-50-50_1024.tif"
OUT_DIR = "/output/portable_project"
os.makedirs(OUT_DIR, exist_ok=True)

app = QgsApplication([], False)
app.initQgis()
project = QgsProject.instance()

raster = QgsRasterLayer(TIF, "Coverage — RF-7800V-HH Repeater 90/50/50")
if not raster.isValid():
    print(f"ERROR: Could not open raster: {TIF}")
    app.exitQgis()
    sys.exit(1)

apply_coverage_style(raster)
project.addMapLayer(raster)

# Save project with relative paths
qgs_path = os.path.join(OUT_DIR, "repeater_coverage_90-50-50.qgs")
project.write(qgs_path)  # type: ignore[arg-type]

# Convert qgs -> qgz (zipped project)
qgz_path = os.path.join(OUT_DIR, "repeater_coverage_90-50-50.qgz")
with zipfile.ZipFile(qgz_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(qgs_path, os.path.basename(qgs_path))
os.remove(qgs_path)

# Export .qml style file (standalone, can be applied to any coverage tif)
qml_path = os.path.join(OUT_DIR, "nowires_coverage_style.qml")
error = ""
raster.saveNamedStyle(qml_path)
if os.path.exists(qml_path):
    print(f"  Style saved: {qml_path} ({os.path.getsize(qml_path)} bytes)")
else:
    print("  [WARN] saveNamedStyle did not produce a file. Writing manual QML.")
    from xml.etree.ElementTree import ElementTree
    doc = raster.exportNamedStyle(QgsMapLayer.StyleCategory.AllStyleCategories)
    if doc:
        tree = ElementTree(doc)
        tree.write(qml_path, xml_declaration=True, encoding="UTF-8")
        print(f"  Style saved (exportNamedStyle): {qml_path}")

# Copy raster into the portable directory (rename for clarity)
tif_dest = os.path.join(OUT_DIR, "repeater_coverage_90-50-50.tif")
shutil.copy2(TIF, tif_dest)

# Also copy reports
for ext in (".csv", ".json", ".html"):
    src = TIF.replace(".tif", ext)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(OUT_DIR, os.path.basename(src)))

print(f"\n  Project:  {qgz_path}")
print(f"  Raster:   {tif_dest}")
print(f"  Style:    {qml_path}")
for f in sorted(os.listdir(OUT_DIR)):
    sz = os.path.getsize(os.path.join(OUT_DIR, f))
    print(f"    {f:<45s} {sz:>8d} bytes")
print(f"\n  Total: {sum(os.path.getsize(os.path.join(OUT_DIR,f)) for f in os.listdir(OUT_DIR))} bytes")

app.exitQgis()
sys.exit(0)
