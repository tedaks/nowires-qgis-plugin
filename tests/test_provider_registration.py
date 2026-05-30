# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Provider registration contract — metadata, algorithm registration, uniqueness.

These tests verify the provider's contract structure (id, name, algorithm
registration count) and that the source code declares the expected algorithms.
Full algorithm instantiation is not tested here because QgsProcessingAlgorithm
requires a real QGIS runtime.

SKIPPED when real QGIS is available because they overwrite sys.modules
with mocks, which segfaults against compiled QGIS extensions.
"""

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent

_HAS_REAL_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))


# Same restoration pattern as test_plugin_load.
_SAVED_MODULES = {
    key: sys.modules.get(key)
    for key in (
        "qgis", "qgis.core", "qgis.PyQt", "qgis.PyQt.QtCore",
        "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets", "qgis.utils",
        "processing", "osgeo", "osgeo.gdal", "osgeo.osr", "osgeo.ogr",
    )
}
_SAVED_NOWIRES_PKG = sys.modules.get("NoWires")

pytestmark = pytest.mark.skipif(
    _HAS_REAL_QGIS,
    reason="Provider registration tests use mock QGIS and must not run against real QGIS extensions",
)


@pytest.fixture(autouse=True)
def _restore_qgis_mocks():
    """Restore conftest QGIS mocks and purge stale module references."""
    for key, saved in _SAVED_MODULES.items():
        if saved is not None:
            sys.modules[key] = saved
    if _SAVED_NOWIRES_PKG is not None:
        sys.modules["NoWires"] = _SAVED_NOWIRES_PKG
    stale_keys = [k for k in list(sys.modules) if k.startswith("NoWires.") and k != "NoWires.__init__"]
    for key in stale_keys:
        mod = sys.modules.get(key)
        if mod is not None and hasattr(mod, "__file__") and mod.__file__ is not None:
            try:
                source = open(mod.__file__).read()
                if "qgis" in source:
                    del sys.modules[key]
            except (OSError, UnicodeDecodeError):
                del sys.modules[key]
    yield


def _make_provider():
    """Create a NoWiresProvider (without loading algorithms)."""
    from NoWires.provider import NoWiresProvider
    return NoWiresProvider()


class TestProviderMetadata:
    def test_provider_id_is_nowires(self):
        p = _make_provider()
        assert p.id() == "nowires"

    def test_provider_name_contains_nowires(self):
        p = _make_provider()
        assert "NoWires" in p.name()

    def test_provider_long_name_describes_purpose(self):
        p = _make_provider()
        name = p.longName()
        assert "Radio" in name or "Propagation" in name


class TestProviderAlgorithmSource:
    """Source-scanning contract: verify the provider registers the expected algorithms."""

    def test_provider_loads_five_algorithms(self):
        """Verify loadAlgorithms() registers exactly 5 algorithms."""
        p = _make_provider()
        p.loadAlgorithms()
        alg_list = list(p.algorithms())
        assert len(alg_list) == 5

    def test_provider_source_lists_expected_algorithms(self):
        """Verify the provider source code references all 5 algorithm modules."""
        source = (_ROOT / "provider.py").read_text()
        for module_name, class_name in [
            ("algorithm.p2p", "P2PAlgorithm"),
            ("algorithm.coverage", "CoverageAlgorithm"),
            ("algorithm.coverage_comparison", "CoverageComparisonAlgorithm"),
            ("algorithm.contour", "ContourLinesAlgorithm"),
            ("algorithm.batch", "BatchAnalysisAlgorithm"),
        ]:
            assert module_name in source, \
                "provider.py must reference {}".format(module_name)
            assert class_name in source, \
                "provider.py must reference {}".format(class_name)

    def test_each_algorithm_class_inherits_qgsprocessing(self):
        """Each algorithm class must inherit from NoWiresAlgorithm."""
        algorithms = [
            ("algorithm.p2p", "P2PAlgorithm"),
            ("algorithm.coverage", "CoverageAlgorithm"),
            ("algorithm.coverage_comparison", "CoverageComparisonAlgorithm"),
            ("algorithm.contour", "ContourLinesAlgorithm"),
            ("algorithm.batch", "BatchAnalysisAlgorithm"),
        ]
        for module_name, class_name in algorithms:
            source = (_ROOT / "{}.py".format(module_name.replace(".", "/"))).read_text()
            assert "NoWiresAlgorithm" in source, \
                "{} must inherit from NoWiresAlgorithm".format(class_name)

    def test_each_algorithm_class_has_name_method(self):
        """Each algorithm module must define a name() method."""
        algorithms = [
            ("algorithm.p2p", "P2PAlgorithm"),
            ("algorithm.coverage", "CoverageAlgorithm"),
            ("algorithm.coverage_comparison", "CoverageComparisonAlgorithm"),
            ("algorithm.contour", "ContourLinesAlgorithm"),
            ("algorithm.batch", "BatchAnalysisAlgorithm"),
        ]
        for module_name, class_name in algorithms:
            source = (_ROOT / "{}.py".format(module_name.replace(".", "/"))).read_text()
            assert "def name(" in source, \
                "{} must define a name() method".format(class_name)

    def test_each_algorithm_class_has_createinstance(self):
        """Each algorithm module must define a createInstance() method."""
        algorithms = [
            ("algorithm.p2p", "P2PAlgorithm"),
            ("algorithm.coverage", "CoverageAlgorithm"),
            ("algorithm.coverage_comparison", "CoverageComparisonAlgorithm"),
            ("algorithm.contour", "ContourLinesAlgorithm"),
            ("algorithm.batch", "BatchAnalysisAlgorithm"),
        ]
        for module_name, class_name in algorithms:
            source = (_ROOT / "{}.py".format(module_name.replace(".", "/"))).read_text()
            assert "def createInstance(" in source, \
                "{} must define a createInstance() method".format(class_name)

    def test_load_algorithms_registers_all_five(self):
        """Verify loadAlgorithms registers exactly 5 algorithms."""
        p = _make_provider()
        p.loadAlgorithms()
        assert len(list(p.algorithms())) == 5
