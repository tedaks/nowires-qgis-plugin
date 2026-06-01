# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""QGIS/osgeo mock stubs and NoWires package registration.

Extracted from conftest.py so that conftest focuses on pytest fixtures
while all the fake-module machinery lives in one dedicated place.
"""

import os
import sys
import types
from unittest.mock import MagicMock

HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
if not HAS_REAL_QGIS:
    try:
        from qgis.core import QgsApplication as _test_QgsApp  # noqa: F401
        HAS_REAL_QGIS = True
    except ImportError:
        pass

HAS_REAL_GDAL = True
try:
    from osgeo import gdal as _test_gdal  # noqa: F401
except ImportError:
    HAS_REAL_GDAL = False


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


def _make_raster_shader(*args, **kwargs):
    m = MagicMock()
    m.setRasterShaderFunction = MagicMock()
    return m


def _make_pseudo_color_renderer(*args, **kwargs):
    return MagicMock()


class _FakeProcessingException(Exception):
    pass


class _FakeQgis:
    class ProcessingAlgorithmFlag:
        NoThreading = 1

    class GeometryType:
        Point = 0

    NULL = MagicMock()


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


class _ParamNumberType:
    Double = 0
    Integer = 1


class _ParamFlag:
    FlagAdvanced = 2


class _ParamNumber:
    Type = _ParamNumberType
    Flag = _ParamFlag
    Double = 0
    Integer = 1
    FlagAdvanced = 2

    def __init__(self, *a, **kw):
        self._name = a[0] if a else ""
        self._description = a[1] if len(a) > 1 else ""
        self.type = _ParamNumberType
        self.defaultValue = kw.get("defaultValue", 0)
        self.minValue = kw.get("minValue", None)
        self.maxValue = kw.get("maxValue", None)
        self.flags = MagicMock(return_value=0)
        self.setFlags = MagicMock()

    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    def minimum(self):
        return self.minValue

    def maximum(self):
        return self.maxValue


def _make_param_point(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    m.flags = MagicMock(return_value=0)
    m.setFlags = MagicMock()
    return m


class _ParamPoint:
    def __new__(cls, *a, **kw):
        return _make_param_point(*a, **kw)


def _make_param_bool(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    m.flags = MagicMock(return_value=0)
    m.setFlags = MagicMock()
    return m


class _ParamBoolean:
    Flag = _ParamFlag
    FlagAdvanced = 2

    def __new__(cls, *a, **kw):
        return _make_param_bool(*a, **kw)


def _make_param_enum(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    m.options = kw.get("options", [])
    m.defaultValue = kw.get("defaultValue", 0)
    m.flags = MagicMock(return_value=0)
    m.setFlags = MagicMock()
    return m


class _ParamEnum:
    def __new__(cls, *a, **kw):
        return _make_param_enum(*a, **kw)


def _make_param_file(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    m.flags = MagicMock(return_value=0)
    m.setFlags = MagicMock()
    return m


class _ParamFile:
    def __new__(cls, *a, **kw):
        return _make_param_file(*a, **kw)


def _make_param_fd(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    return m


class _ParamFileDest:
    def __new__(cls, *a, **kw):
        return _make_param_fd(*a, **kw)


def _make_param_str(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    return m


class _ParamString:
    def __new__(cls, *a, **kw):
        return _make_param_str(*a, **kw)


def _make_param_field(*a, **kw):
    m = MagicMock()
    m.name = a[0] if a else ""
    m.description = a[1] if len(a) > 1 else ""
    return m


class _ParamField:
    def __new__(cls, *a, **kw):
        return _make_param_field(*a, **kw)


_mock_registry = MagicMock()


class _FakeQgsApplication:
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def processingRegistry():
        return _mock_registry

    @staticmethod
    def instance():
        return None

    @staticmethod
    def initQgis():
        pass

    @staticmethod
    def exitQgis():
        pass


_QGIS_CORE_ATTRS = {
    "QgsProcessingException": _FakeProcessingException,
    "QgsColorRampShader": _ColorRampShader,
    "QgsRasterShader": _make_raster_shader,
    "QgsSingleBandPseudoColorRenderer": _make_pseudo_color_renderer,
    "QgsVectorLayer": MagicMock,
    "QgsRasterLayer": MagicMock,
    "QgsProject": MagicMock(),
    "QgsProject.instance": MagicMock(),
    "QgsMessageLog": MagicMock(),
    "Qgis": _FakeQgis,
    "QgsProcessingAlgorithm": MagicMock,
    "QgsProcessingContext": MagicMock,
    "QgsCoordinateReferenceSystem": MagicMock,
    "QgsCoordinateTransform": MagicMock,
    "QgsAuthMethodConfig": MagicMock,
    "QgsRasterDemTerrainProvider": MagicMock,
    "QgsProcessingParameterNumber": _ParamNumber,
    "QgsProcessingParameterPoint": _ParamPoint,
    "QgsProcessingParameterBoolean": _ParamBoolean,
    "QgsProcessingParameterEnum": _ParamEnum,
    "QgsProcessingParameterFile": _ParamFile,
    "QgsProcessingParameterFileDestination": _ParamFileDest,
    "QgsProcessingParameterString": _ParamString,
    "QgsProcessingParameterField": _ParamField,
    "NULL": MagicMock(),
    "QT_VERSION_STR": "6.0.0",
    "QgsApplication": _FakeQgsApplication,
}

_QGIS_PROCESSING_PROVIDER = type(
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

_QGIS_PYQT_WIDGETS_ATTRS = {
    "QDialog": type(
        "QDialog", (), {
            "__init__": lambda self, parent=None: None,
            "setModal": lambda self, m: None,
            "setWindowTitle": lambda self, t: None,
            "setWindowFlag": lambda self, *a, **kw: None,
            "setMinimumWidth": lambda self, w: None,
            "show": lambda self: None,
            "close": lambda self: None,
        },
    ),
    "QSlider": _mock_qslider_factory,
    "QVBoxLayout": _mock_layout_factory,
    "QHBoxLayout": _mock_layout_factory,
    "QLabel": _make_qlabel,
    "QInputDialog": MagicMock,
    "QCheckBox": MagicMock,
    "QMessageBox": MagicMock,
    "QFileDialog": MagicMock,
    "QFrame": MagicMock,
    "QWidget": MagicMock,
}


def install_qgis_mocks():
    """Install QGIS/osgeo mock modules into sys.modules.

    Does nothing if a real QGIS runtime is detected.
    """
    if HAS_REAL_QGIS:
        return

    if not HAS_REAL_GDAL:
        sys.modules["osgeo"] = MagicMock()
        sys.modules["osgeo.gdal"] = MagicMock()
        sys.modules["osgeo.osr"] = MagicMock()
        sys.modules["osgeo.ogr"] = MagicMock()

    _qgis = types.ModuleType("qgis")
    _qgis_core = types.ModuleType("qgis.core")

    for attr, val in _QGIS_CORE_ATTRS.items():
        setattr(_qgis_core, attr, val)

    _qgis_core.QgsProcessingProvider = _QGIS_PROCESSING_PROVIDER

    # __getattr__ returns MagicMock for any QGIS type not explicitly listed.
    _qgis_core.__getattr__ = lambda name: MagicMock(name=f"qgis.core.{name}")

    sys.modules.setdefault("qgis", _qgis)
    sys.modules.setdefault("qgis.core", _qgis_core)
    _qgis.core = _qgis_core

    # --- PyQt stubs ---
    _qgis_pyqt = types.ModuleType("qgis.PyQt")
    _qgis_pyqtQtCore = types.ModuleType("qgis.PyQt.QtCore")
    _qgis_pyqtQtGui = types.ModuleType("qgis.PyQt.QtGui")
    _qgis_pyqtQtWidgets = types.ModuleType("qgis.PyQt.QtWidgets")

    _qgis_pyqtQtCore.Qt = MagicMock()
    _qgis_pyqtQtCore.QTimer = MagicMock()
    _qgis_pyqtQtCore.QEvent = MagicMock()
    _qgis_pyqtQtCore.QCoreApplication = MagicMock()
    _qgis_pyqtQtCore.QPointF = MagicMock()
    _qgis_pyqtQtCore.QT_VERSION_STR = "6.0.0"
    _qgis_pyqtQtGui.QAction = _make_qaction
    _qgis_pyqtQtGui.QIcon = _make_qicon
    _qgis_pyqtQtGui.QPixmap = _make_qpixmap
    _qgis_pyqtQtGui.QColor = _make_qcolor
    _qgis_pyqtQtGui.QPainter = _make_qpainter
    _qgis_pyqtQtGui.QFont = MagicMock()
    _qgis_pyqtQtGui.QPen = MagicMock()
    _qgis_pyqtQtGui.QPolygonF = MagicMock()

    for attr, val in _QGIS_PYQT_WIDGETS_ATTRS.items():
        setattr(_qgis_pyqtQtWidgets, attr, val)
    _qgis_pyqtQtWidgets.__getattr__ = lambda name: MagicMock(name=f"qgis.PyQt.QtWidgets.{name}")
    _qgis_pyqtQtGui.__getattr__ = lambda name: MagicMock(name=f"qgis.PyQt.QtGui.{name}")
    _qgis_pyqtQtCore.__getattr__ = lambda name: MagicMock(name=f"qgis.PyQt.QtCore.{name}")

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
    _qgis.utils = _qgis_utils

    # --- processing stub ---
    sys.modules.setdefault("processing", MagicMock())


_TOP_LEVEL_SUBMODULES = (
    "antenna",
    "constants",
    "macos_compat",
    "reliability",
    "overlay_raster",
    "nan_utils",
)
_PACKAGE_SUBMODULES = (
    # algorithm/
    "algorithm.p2p",
    "algorithm.coverage",
    "algorithm._coverage_helpers",
    "algorithm._project_paths",
    "algorithm.coverage_comparison",
    "algorithm.batch",
    # batch/
    "batch.outputs",
    "batch.params",
    "batch.writer",
    "batch.analysis_params",
    # comparison/
    "comparison.outputs",
    "comparison.panel",
    "comparison.params",
    "comparison.reporting",
    "comparison.add_params",
    # radio_coverage/
    "radio_coverage.compute",
    "radio_coverage.engine",
    "radio_coverage.pool",
    "radio_coverage.tasks",
    "radio_coverage.summary",
    "radio_coverage.params",
    "radio_coverage.analysis_params",
    "radio_coverage.palette",
    "radio_coverage.legend",
    "radio_coverage.opacity",
    "radio_coverage.reporting",
    "radio_coverage.dem_validate",
    "radio_coverage._executor",
    "radio_coverage.result_dispatch",
    "radio_coverage.coverage_grids",
    # clutter/ — package is registered as "clutter" (its __init__.py is the
    # facade); list only submodules below. Do NOT list "clutter.__init__".
    "clutter",
    "clutter.advanced",
    "clutter.categories",
    "clutter.constants",
    "clutter.context",
    "clutter.grid",
    "clutter.resolve",
    "clutter.p833",
    "clutter.p2108_common",
    "clutter.p2108_height_gain",
    "clutter.p2108_terrestrial_stat",
    "clutter.p2109_bel",
    # p2p/
    "p2p.compute",
    "p2p.outputs",
    "p2p.params",
    "p2p.chart",
    "p2p.chart_format",
    "p2p.symbology",
    "p2p.report_display",
    "p2p.analysis_params",
    "p2p.outputs_internal",
    "p2p.chart_params",
    # report/
    "report.export",
    "report.markers",
    "report.payloads",
    "report.pdf",
    # benchmarks/ (unchanged)
    "benchmarks.coverage_runtime",
    "benchmarks.p2p_runtime",
    "benchmarks.reference_cases",
    # root-staying modules
    "radio",
    "fresnel",
    "elevation",
    "geo_bounds",
    "_geo_utils",
    "_bilinear",
    "shared_params",
    "shared_dem_grid",
    "dem_downloader",
    "worldcover_downloader",
    "tile_download_base",
    "cache_manager",
    "windows_compat",
)


def register_nowires_package():
    """Register the NoWires package and submodules in sys.modules."""
    import importlib.util as _ilu

    plugin_dir = os.path.join(os.path.dirname(__file__), "..")
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    _no_wires_pkg = types.ModuleType("NoWires")
    _no_wires_pkg.__path__ = [plugin_dir]
    _no_wires_pkg.__package__ = "NoWires"
    _no_wires_pkg.__name__ = "NoWires"
    sys.modules["NoWires"] = _no_wires_pkg

    _init_spec = _ilu.spec_from_file_location(
        "NoWires", os.path.join(plugin_dir, "__init__.py"),
        submodule_search_locations=[plugin_dir],
    )
    _init_mod = _ilu.module_from_spec(_init_spec)
    _init_spec.loader.exec_module(_init_mod)
    for _attr in ("classFactory", "_NoOpPlugin"):
        if hasattr(_init_mod, _attr):
            setattr(_no_wires_pkg, _attr, getattr(_init_mod, _attr))

    # Register subpackage __init__.py modules as packages first, so
    # that importing their children finds a proper parent package.
    _SUBPKG_DIRS = (
        "algorithm",
        "batch",
        "comparison",
        "radio_coverage",
        "clutter",
        "p2p",
        "report",
    )
    _SUBPKG_DIR_SET = set(_SUBPKG_DIRS)
    for _subpkg in _SUBPKG_DIRS:
        _subpkg_dir = os.path.join(plugin_dir, _subpkg)
        _subpkg_mod = types.ModuleType(f"NoWires.{_subpkg}")
        _subpkg_mod.__path__ = [_subpkg_dir]
        _subpkg_mod.__package__ = f"NoWires.{_subpkg}"
        _subpkg_mod.__name__ = f"NoWires.{_subpkg}"
        # Load and exec the subpackage __init__.py
        _subpkg_init = os.path.join(_subpkg_dir, "__init__.py")
        if os.path.isfile(_subpkg_init):
            _spec = _ilu.spec_from_file_location(
                f"NoWires.{_subpkg}", _subpkg_init,
                submodule_search_locations=[_subpkg_dir],
            )
            _mod = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            _subpkg_mod = _mod
            _subpkg_mod.__path__ = [_subpkg_dir]
        sys.modules[f"NoWires.{_subpkg}"] = _subpkg_mod
        setattr(_no_wires_pkg, _subpkg, _subpkg_mod)
        # Register subpkg as top-level name so bare imports
        # (e.g. "from radio_coverage.pool import X") resolve.
        # This ensures bare imports like "from radio_coverage.engine import ..."
        # find our subpackage.
        sys.modules[_subpkg] = _subpkg_mod

    for _submodule_name in _TOP_LEVEL_SUBMODULES:
        _mod = __import__(_submodule_name, fromlist=[""])
        sys.modules[f"NoWires.{_submodule_name}"] = _mod
        setattr(_no_wires_pkg, _submodule_name, _mod)

    for _pkg_sub in _PACKAGE_SUBMODULES:
        _mod = __import__(f"NoWires.{_pkg_sub}", fromlist=[""])
        _leaf = _pkg_sub.split(".")[-1]
        sys.modules[f"NoWires.{_pkg_sub}"] = _mod
        # Also register under the bare dotted path (e.g. "clutter.categories")
        # so that "from clutter.categories import X" resolves correctly.
        # Python's __import__ only caches under "NoWires.clutter.categories".
        sys.modules[_pkg_sub] = _mod
        # Set module as attribute on parent package so that
        # getattr(parent_mod, _leaf) works (needed for monkeypatch).
        _parent_name = _pkg_sub.rsplit(".", 1)[0] if "." in _pkg_sub else None
        if _parent_name is not None:
            _parent_mod = sys.modules.get(f"NoWires.{_parent_name}")
            if _parent_mod is not None:
                setattr(_parent_mod, _leaf, _mod)
        # Do NOT overwrite subpackage entries on _no_wires_pkg:
        # e.g. _pkg_sub="algorithm.coverage" has _leaf="coverage", which has
        # historically been a potential collision point with subpackage names.
        _parent = _pkg_sub.split(".")[0] if "." in _pkg_sub else None
        if _parent not in _SUBPKG_DIR_SET:
            setattr(_no_wires_pkg, _leaf, _mod)
            if _leaf not in sys.modules:
                sys.modules[_leaf] = _mod