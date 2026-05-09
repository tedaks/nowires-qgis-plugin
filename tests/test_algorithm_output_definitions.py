# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify all 5 algorithms declare correct output definitions."""

import os
import pytest

try:
    from qgis.core import QgsApplication
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(
        not _HAS_QGIS,
        reason="QGIS integration tests require QGIS_PREFIX_PATH to be set",
    ),
    pytest.mark.qgis_integration,
]


@pytest.fixture(scope="module")
def qgis_app():
    qgis = QgsApplication([], True)
    qgis.initQgis()
    yield qgis
    qgis.exitQgis()


@pytest.fixture
def provider(qgis_app):
    from NoWires.provider import NoWiresProvider
    p = NoWiresProvider()
    p.loadAlgorithms()
    return p


def _init_alg(provider, name):
    for alg in provider.algorithms():
        if alg.name() == name:
            alg.initAlgorithm("")
            return alg
    pytest.skip("Algorithm {} not found".format(name))


EXPECTED_P2P_OUTPUTS = [
    "OUTPUT_PROFILE", "OUTPUT_FRESNEL", "OUTPUT_MARKERS",
    "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON", "OUTPUT_REPORT_HTML",
]

EXPECTED_COVERAGE_OUTPUTS = [
    "OUTPUT_RASTER", "OUTPUT_REPORT_CSV",
    "OUTPUT_REPORT_JSON", "OUTPUT_REPORT_HTML",
]

EXPECTED_CONTOUR_OUTPUTS = ["OUTPUT", "OUTPUT_DEM"]

EXPECTED_COMPARISON_OUTPUTS = [
    "OUTPUT_A", "OUTPUT_B", "OUTPUT_DELTA", "OUTPUT_REPORT_HTML",
]

EXPECTED_BATCH_OUTPUTS = ["OUTPUT_MARKERS", "OUTPUT_CSV", "OUTPUT_JSON"]


class TestP2POutputDefinitions:
    def test_output_names(self, provider):
        alg = _init_alg(provider, "p2p_analysis")
        output_names = [o.name() for o in alg.outputDefinitions()]
        for expected in EXPECTED_P2P_OUTPUTS:
            assert expected in output_names, "Missing output: {}".format(expected)

    def test_profile_output_is_vector(self, provider):
        alg = _init_alg(provider, "p2p_analysis")
        from qgis.core import QgsProcessingOutputVectorLayer
        out = alg.outputDefinition("OUTPUT_PROFILE")
        assert isinstance(out, QgsProcessingOutputVectorLayer)

    def test_fresnel_output_is_vector(self, provider):
        alg = _init_alg(provider, "p2p_analysis")
        from qgis.core import QgsProcessingOutputVectorLayer
        out = alg.outputDefinition("OUTPUT_FRESNEL")
        assert isinstance(out, QgsProcessingOutputVectorLayer)


class TestCoverageOutputDefinitions:
    def test_output_names(self, provider):
        alg = _init_alg(provider, "coverage_analysis")
        output_names = [o.name() for o in alg.outputDefinitions()]
        for expected in EXPECTED_COVERAGE_OUTPUTS:
            assert expected in output_names, "Missing output: {}".format(expected)

    def test_raster_output_type(self, provider):
        alg = _init_alg(provider, "coverage_analysis")
        from qgis.core import QgsProcessingOutputRasterLayer
        out = alg.outputDefinition("OUTPUT_RASTER")
        assert isinstance(out, QgsProcessingOutputRasterLayer)


class TestContourOutputDefinitions:
    def test_output_names(self, provider):
        alg = _init_alg(provider, "contour_lines")
        output_names = [o.name() for o in alg.outputDefinitions()]
        for expected in EXPECTED_CONTOUR_OUTPUTS:
            assert expected in output_names, "Missing output: {}".format(expected)

    def test_contour_output_is_vector(self, provider):
        alg = _init_alg(provider, "contour_lines")
        from qgis.core import QgsProcessingOutputVectorLayer
        out = alg.outputDefinition("OUTPUT")
        assert isinstance(out, QgsProcessingOutputVectorLayer)


class TestComparisonOutputDefinitions:
    def test_output_names(self, provider):
        alg = _init_alg(provider, "coverage_comparison")
        output_names = [o.name() for o in alg.outputDefinitions()]
        for expected in EXPECTED_COMPARISON_OUTPUTS:
            assert expected in output_names, "Missing output: {}".format(expected)

    def test_raster_outputs_are_raster_type(self, provider):
        alg = _init_alg(provider, "coverage_comparison")
        from qgis.core import QgsProcessingOutputRasterLayer
        for name in ("OUTPUT_A", "OUTPUT_B", "OUTPUT_DELTA"):
            out = alg.outputDefinition(name)
            assert isinstance(out, QgsProcessingOutputRasterLayer)


class TestBatchOutputDefinitions:
    def test_output_names(self, provider):
        alg = _init_alg(provider, "batch_p2p_analysis")
        output_names = [o.name() for o in alg.outputDefinitions()]
        for expected in EXPECTED_BATCH_OUTPUTS:
            assert expected in output_names, "Missing output: {}".format(expected)