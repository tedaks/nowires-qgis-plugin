# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""pytest configuration.

When tests are run via ``pytest tests/`` from the repo root (no QGIS
installed), the osgeo and qgis modules are not available. This conftest:

1. Mocks osgeo/gdal/ogr so modules that transitively import it don't fail.
2. Creates a fake ``NoWires`` package in sys.modules so that relative
   imports inside the plugin (e.g. ``from .antenna import ...``) resolve
   to the actual plugin modules already on sys.path.
3. Ensures that when coverage_engine is imported through the package
   (NoWires.coverage_engine), its __spec__.parent is set to "NoWires" so
   relative imports resolve correctly.
4. Mocks qgis.PyQt, qgis.utils, processing, and QgsProcessingProvider
   so that plugin lifecycle and dialog tests work without a QGIS runtime.
5. Provides explicit stubs for all QGIS types used by the plugin, rather
   than a broad __getattr__, to avoid interfering with other test files
   that set up their own QGIS mocks.

When a real QGIS runtime is available (QGIS_PREFIX_PATH set or qgis.core
importable), all mocking is skipped so integration tests use the real QGIS.
"""

import os
import sys
import types
from unittest.mock import MagicMock

# Detect whether a real QGIS runtime is available.
# When running inside the QGIS container (or with QGIS_PREFIX_PATH set),
# we should NOT mock qgis modules — let the real ones load.
_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
if not _HAS_REAL_QGIS:
    try:
        from qgis.core import QgsApplication as _test_QgsApp  # noqa: F401
        _HAS_REAL_QGIS = True
    except ImportError:
        pass


def _mock_factory(*args, _return_mock=None, **kwargs):
    """Create a callable that returns a MagicMock, avoiding InvalidSpecError."""
    m = MagicMock()
    if _return_mock is not None:
        return _return_mock
    return m


def _mock_layout_factory(*args, **kwargs):
    """Factory for QVBoxLayout/QHBoxLayout that returns unspecced MagicMock."""
    return MagicMock()


def _mock_qslider_factory(*args, **kwargs):
    """Factory for QSlider that returns unspecced MagicMock with TickPosition."""
    return MagicMock()


_mock_qslider_factory.TickPosition = MagicMock()
_mock_qslider_factory.TickPosition.TicksBelow = 0
_mock_qslider_factory.TickPosition.TicksAbove = 1
_mock_qslider_factory.TickPosition.NoTicks = 2


# If a real QGIS runtime is available, skip all mocking so integration
# tests use the real QGIS classes.
if not _HAS_REAL_QGIS:

    sys.modules["osgeo"] = MagicMock()
    sys.modules["osgeo.gdal"] = MagicMock()
    sys.modules["osgeo.osr"] = MagicMock()
    sys.modules["osgeo.ogr"] = MagicMock()

    _qgis = types.ModuleType("qgis")
    _qgis_core = types.ModuleType("qgis.core")

    class _FakeProcessingException(Exception):
        pass

    class _FakeQgis:
        class ProcessingAlgorithmFlag:
            NoThreading = 1
        class GeometryType:
            Point = 0
        NULL = MagicMock()

    # Explicitly set all QGIS types used by the plugin on _qgis_core.
    _qgis_core.QgsProcessingException = _FakeProcessingException

    # --- Color ramp shader stubs ---
    class _ColorRampItem:
        def __init__(self, value, color, label):
            self.value = value
            self.color = color
            self.label = label

    class _ColorRampShader:
        Discrete = 0
        Interpolated = 1
        ColorRampItem = _ColorRampItem

        def __new__(cls, *args, **kwargs):
            instance = MagicMock()
            instance.setColorRampItemList = MagicMock()
            instance.setColorRampType = MagicMock()
            instance.setColorRampItemList.return_value = None
            instance.setColorRampType.return_value = None
            return instance

    _qgis_core.QgsColorRampShader = _ColorRampShader

    # --- Raster shader stubs that avoid InvalidSpecError ---
    def _make_raster_shader(*args, **kwargs):
        m = MagicMock()
        m.setRasterShaderFunction = MagicMock()
        return m

    def _make_pseudo_color_renderer(*args, **kwargs):
        return MagicMock()

    _qgis_core.QgsRasterShader = _make_raster_shader
    _qgis_core.QgsSingleBandPseudoColorRenderer = _make_pseudo_color_renderer
    _qgis_core.QgsVectorLayer = MagicMock
    _qgis_core.QgsRasterLayer = MagicMock
    _qgis_core.QgsProject = MagicMock()
    _qgis_core.QgsProject.instance = MagicMock()
    _qgis_core.QgsMessageLog = MagicMock()
    _qgis_core.Qgis = _FakeQgis
    _qgis_core.QgsProcessingAlgorithm = MagicMock
    _qgis_core.QgsProcessingContext = MagicMock
    _qgis_core.QgsCoordinateReferenceSystem = MagicMock
    _qgis_core.QgsCoordinateTransform = MagicMock
    _qgis_core.QgsAuthMethodConfig = MagicMock
    _qgis_core.QgsRasterDemTerrainProvider = MagicMock

    # --- Processing parameter stubs with enum-like attributes ---
    class _ParamNumber:
        Double = 0
        Integer = 1
        FlagAdvanced = 2
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamPoint:
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamBoolean:
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamEnum:
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamFile:
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamFileDest:
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamString:
        def __call__(self, *a, **kw):
            return MagicMock()

    class _ParamField:
        def __call__(self, *a, **kw):
            return MagicMock()

    _qgis_core.QgsProcessingParameterNumber = _ParamNumber
    _qgis_core.QgsProcessingParameterPoint = _ParamPoint
    _qgis_core.QgsProcessingParameterBoolean = _ParamBoolean
    _qgis_core.QgsProcessingParameterEnum = _ParamEnum
    _qgis_core.QgsProcessingParameterFile = _ParamFile
    _qgis_core.QgsProcessingParameterFileDestination = _ParamFileDest
    _qgis_core.QgsProcessingParameterString = _ParamString
    _qgis_core.QgsProcessingParameterField = _ParamField

    # __getattr__ returns MagicMock for any QGIS type not explicitly listed.
    _qgis_core.__getattr__ = lambda name: MagicMock(name=f"qgis.core.{name}")
    _qgis_core.NULL = MagicMock()
    _qgis_core.QT_VERSION_STR = "6.0.0"

    # --- Processing provider stub ---
    _qgis_core.QgsProcessingProvider = type(
        "QgsProcessingProvider", (), {
            "__init__": lambda self: setattr(self, "_algorithms", []) or None,
            "addAlgorithm": lambda self, alg: self._algorithms.append(alg),
            "algorithms": lambda self: list(self._algorithms),
            "id": lambda self: "",
            "name": lambda self: "",
            "unload": lambda self: None,
            "tr": lambda self, s: s,
            "loadAlgorithms": lambda self: None,
        },
    )

    # --- QgsApplication stub ---
    _mock_registry = MagicMock()

    class _FakeQgsApplication:
        @staticmethod
        def processingRegistry():
            return _mock_registry

    _qgis_core.QgsApplication = _FakeQgsApplication

    sys.modules.setdefault("qgis", _qgis)
    sys.modules.setdefault("qgis.core", _qgis_core)

    # --- PyQt stubs ---
    def _make_qicon(*args, **kwargs):
        return MagicMock()

    def _make_qpixmap(*args, **kwargs):
        return MagicMock()

    def _make_qaction(*args, **kwargs):
        return MagicMock()

    def _make_qcolor(*args, **kwargs):
        return MagicMock()

    def _make_qpainter(*args, **kwargs):
        return MagicMock()

    def _make_qlabel(*args, **kwargs):
        return MagicMock()

    _qgis_pyqt = types.ModuleType("qgis.PyQt")
    _qgis_pyqtQtCore = types.ModuleType("qgis.PyQt.QtCore")
    _qgis_pyqtQtGui = types.ModuleType("qgis.PyQt.QtGui")
    _qgis_pyqtQtWidgets = types.ModuleType("qgis.PyQt.QtWidgets")

    _qgis_pyqtQtCore.Qt = MagicMock()
    _qgis_pyqtQtCore.QTimer = MagicMock()
    _qgis_pyqtQtCore.QEvent = MagicMock()
    _qgis_pyqtQtCore.QCoreApplication = MagicMock()
    _qgis_pyqtQtCore.QT_VERSION_STR = "6.0.0"
    _qgis_pyqtQtGui.QAction = _make_qaction
    _qgis_pyqtQtGui.QIcon = _make_qicon
    _qgis_pyqtQtGui.QPixmap = _make_qpixmap
    _qgis_pyqtQtGui.QColor = _make_qcolor
    _qgis_pyqtQtGui.QPainter = _make_qpainter
    _qgis_pyqtQtWidgets.QDialog = type(
        "QDialog", (), {
            "__init__": lambda self, parent=None: None,
            "setModal": lambda self, m: None,
            "setWindowTitle": lambda self, t: None,
            "setMinimumWidth": lambda self, w: None,
            "show": lambda self: None,
            "close": lambda self: None,
        },
    )
    _qgis_pyqtQtWidgets.QSlider = _mock_qslider_factory
    _qgis_pyqtQtWidgets.QVBoxLayout = _mock_layout_factory
    _qgis_pyqtQtWidgets.QHBoxLayout = _mock_layout_factory
    _qgis_pyqtQtWidgets.QLabel = _make_qlabel
    _qgis_pyqtQtWidgets.QInputDialog = MagicMock
    _qgis_pyqtQtWidgets.QCheckBox = MagicMock
    _qgis_pyqtQtWidgets.QMessageBox = MagicMock
    _qgis_pyqtQtWidgets.QFileDialog = MagicMock
    _qgis_pyqtQtWidgets.QFrame = MagicMock
    _qgis_pyqtQtWidgets.QWidget = MagicMock

    _qgis_pyqt.QtCore = _qgis_pyqtQtCore
    _qgis_pyqt.QtGui = _qgis_pyqtQtGui
    _qgis_pyqt.QtWidgets = _qgis_pyqtQtWidgets

    sys.modules.setdefault("qgis.PyQt", _qgis_pyqt)
    sys.modules.setdefault("qgis.PyQt.QtCore", _qgis_pyqtQtCore)
    sys.modules.setdefault("qgis.PyQt.QtGui", _qgis_pyqtQtGui)
    sys.modules.setdefault("qgis.PyQt.QtWidgets", _qgis_pyqtQtWidgets)

    # --- qgis.utils stub ---
    _qgis_utils = types.ModuleType("qgis.utils")
    _qgis_utils.iface = None
    sys.modules.setdefault("qgis.utils", _qgis_utils)

    # --- processing stub ---
    sys.modules.setdefault("processing", MagicMock())

# --- NoWires package registration (always runs) ---
plugin_dir = os.path.join(os.path.dirname(__file__), "..")
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

_no_wires_pkg = types.ModuleType("NoWires")
_no_wires_pkg.__path__ = [plugin_dir]
_no_wires_pkg.__package__ = "NoWires"
_no_wires_pkg.__name__ = "NoWires"
sys.modules["NoWires"] = _no_wires_pkg

import importlib.util as _ilu

_init_spec = _ilu.spec_from_file_location(
    "NoWires", os.path.join(plugin_dir, "__init__.py"),
    submodule_search_locations=[plugin_dir],
)
_init_mod = _ilu.module_from_spec(_init_spec)
_init_spec.loader.exec_module(_init_mod)
for _attr in ("classFactory", "_NoOpPlugin"):
    if hasattr(_init_mod, _attr):
        setattr(_no_wires_pkg, _attr, getattr(_init_mod, _attr))

# Submodules with no relative imports and no top-level qgis dependency —
# can be loaded as top-level first, then registered under the NoWires package.
for _submodule_name in (
    "antenna",
    "coverage_palette",
    "macos_compat",
    "reliability",
    "p2p_report_display",
    "comparison_reporting",
    "contour_smoothing",
    "report_markers",
    "report_export",
    "overlay_raster",
    "nan_utils",
):
    _mod = __import__(_submodule_name, fromlist=[""])
    sys.modules[f"NoWires.{_submodule_name}"] = _mod
    setattr(_no_wires_pkg, _submodule_name, _mod)

# Submodules that use relative imports and have no top-level qgis dependency —
# must be imported through the NoWires package so ``from .xxx import ...`` resolves.
for _pkg_sub in (
    "radio",
    "coverage_compute",
    "coverage_summary",
    "fresnel",
    "elevation",
    "coverage_engine",
    "report_payloads",
    "clutter",
    "clutter_saalos",
    "clutter_p2108",
    "clutter_categories",
    "clutter_constants",
    "clutter_context",
    "clutter_advanced",
    "p2108_common",
    "p2108_terrestrial_stat",
    "p2108_height_gain",
    "p2109_bel",
    "tile_download_base",
    "worldcover_downloader",
    "p2p_outputs",
    "p2p_chart",
    "coverage_pool",
    "coverage_tasks",
    "contour_overlay",
    "contour_generation",
    "comparison_outputs",
    "coverage_opacity",
    "coverage_legend",
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