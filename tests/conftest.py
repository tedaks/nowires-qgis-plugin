# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""pytest configuration.

When tests are run via ``pytest tests/`` from the repo root, the osgeo
module is not available (it ships with QGIS). This conftest:

1. Mocks osgeo/gdal so modules that transitively import it don't fail.
2. Creates a fake ``NoWires`` package in sys.modules so that relative
   imports inside the plugin (e.g. ``from .antenna import ...``) resolve
   to the actual plugin modules already on sys.path.
3. Ensures that when coverage_engine is imported through the package
   (NoWires.coverage_engine), its __spec__.parent is set to "NoWires" so
   relative imports resolve correctly.
"""

import os
import sys
import types
from unittest.mock import MagicMock

sys.modules["osgeo"] = MagicMock()
sys.modules["osgeo.gdal"] = MagicMock()

plugin_dir = os.path.join(os.path.dirname(__file__), "..")
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

_no_wires_pkg = types.ModuleType("NoWires")
_no_wires_pkg.__path__ = [plugin_dir]
_no_wires_pkg.__package__ = "NoWires"
_no_wires_pkg.__name__ = "NoWires"
sys.modules["NoWires"] = _no_wires_pkg

# Submodules with no relative imports and no top-level qgis dependency —
# can be loaded as top-level first, then registered under the NoWires package.
for _submodule_name in (
    "antenna",
    "coverage_palette",
    "coverage_summary",
    "elevation",
    "reliability",
    "fresnel",
    "tile_download_base",
    "p2p_report_display",
    "comparison_reporting",
    "contour_smoothing",
    "report_markers",
    "report_export",
    "overlay_raster",
):
    _mod = __import__(_submodule_name, fromlist=[""])
    sys.modules[f"NoWires.{_submodule_name}"] = _mod
    setattr(_no_wires_pkg, _submodule_name, _mod)

# Submodules that use relative imports and have no top-level qgis dependency —
# must be imported through the NoWires package so ``from .xxx import ...`` resolves.
for _pkg_sub in (
    "radio",
    "coverage_compute",
    "coverage_engine",
    "report_payloads",
    "clutter",
    "worldcover_downloader",
    "p2p_outputs",
    "p2p_chart",
    "coverage_pool",
    "coverage_tasks",
    "contour_overlay",
    "contour_generation",
    "benchmarks.coverage_runtime",
    "benchmarks.p2p_runtime",
    "benchmarks.reference_cases",
):
    _mod = __import__(f"NoWires.{_pkg_sub}", fromlist=[""])
    _leaf = _pkg_sub.split(".")[-1]
    sys.modules[f"NoWires.{_pkg_sub}"] = _mod
    setattr(_no_wires_pkg, _leaf, _mod)
    if _leaf not in sys.modules:
        sys.modules[_leaf] = _mod
