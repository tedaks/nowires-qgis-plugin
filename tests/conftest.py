# -*- coding: utf-8 -*-
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

for _submodule_name in (
    "antenna",
    "coverage_palette",
    "coverage_summary",
    "elevation",
    "radio",
):
    _mod = __import__(_submodule_name, fromlist=[""])
    sys.modules[f"NoWires.{_submodule_name}"] = _mod
    setattr(_no_wires_pkg, _submodule_name, _mod)

_coverage_mod = __import__("NoWires.coverage_engine", fromlist=[""])
sys.modules["coverage_engine"] = _coverage_mod
sys.modules["NoWires.coverage_engine"] = _coverage_mod
setattr(_no_wires_pkg, "coverage_engine", _coverage_mod)
