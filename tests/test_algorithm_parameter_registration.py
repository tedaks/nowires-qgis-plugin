# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify all 5 algorithms register their parameters correctly with QGIS."""

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


def _get_algorithm(provider, name):
    for alg in provider.algorithms():
        if alg.name() == name:
            alg.initAlgorithm("")
            return alg
    pytest.skip("Algorithm {} not found".format(name))


EXPECTED_P2P_PARAMS = [
    "TX_POINT", "RX_POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ",
    "POLARIZATION", "CLIMATE", "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT",
    "TX_POWER", "TX_GAIN", "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY",
    "TX_ANTENNA_PRESET", "TX_ANTENNA_AZ", "TX_FRONT_BACK_DB",
    "TX_DOWNTILT_DEG", "TX_H_PATTERN", "TX_V_PATTERN",
    "RX_ANTENNA_PRESET", "RX_ANTENNA_AZ", "RX_FRONT_BACK_DB",
    "RX_DOWNTILT_DEG", "RX_H_PATTERN", "RX_V_PATTERN",
    "CLUTTER_MODEL", "CLUTTER_RASTER", "TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE", "CCH_OVERRIDE", "CLUTTER_PERCENTILE",
    "STREET_WIDTH", "BEL_ENABLED", "BEL_BUILDING_TYPE",
    "BEL_ELEVATION_ANGLE",
    "K_FACTOR_PRESET", "K_FACTOR", "N0", "EPSILON", "SIGMA",
    "OUTPUT_PROFILE", "OUTPUT_FRESNEL", "OUTPUT_MARKERS",
    "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON", "OUTPUT_REPORT_HTML",
    "SHOW_CHART",
]

EXPECTED_COVERAGE_PARAMS = [
    "TX_POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "RADIUS_KM",
    "GRID_SIZE", "POLARIZATION", "CLIMATE",
    "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT",
    "TX_POWER", "TX_GAIN", "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY",
    "ANTENNA_BW", "ANTENNA_AZ", "ANTENNA_PRESET",
    "FRONT_BACK_DB", "DOWNTILT_DEG", "H_PATTERN", "V_PATTERN",
    "CLUTTER_MODEL", "CLUTTER_RASTER", "TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE", "CCH_OVERRIDE",
    "CLUTTER_PERCENTILE", "STREET_WIDTH", "BEL_ENABLED",
    "BEL_BUILDING_TYPE", "BEL_ELEVATION_ANGLE",
    "N0", "EPSILON", "SIGMA",
    "OUTPUT_RASTER", "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON",
    "OUTPUT_REPORT_HTML",
]

EXPECTED_CONTOUR_PARAMS = [
    "AREA_OF_INTEREST", "INTERVAL", "UNIT", "SMOOTHING", "COLOR",
    "ELEVATION_MAP", "PROXY_AUTH", "OUTPUT", "OUTPUT_DEM",
]

EXPECTED_BATCH_PARAMS = [
    "MODE", "TX_POINT", "RX_LAYER", "RX_POINT", "TX_LAYER",
    "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "POLARIZATION", "CLIMATE",
    "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT",
    "TX_POWER", "TX_GAIN", "RX_GAIN", "CABLE_LOSS", "RX_SENSITIVITY",
    "TX_ANTENNA_PRESET", "TX_ANTENNA_AZ", "TX_FRONT_BACK_DB",
    "RX_ANTENNA_PRESET", "RX_ANTENNA_AZ", "RX_FRONT_BACK_DB",
    "CLUTTER_MODEL", "CLUTTER_RASTER", "TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE",
    "K_FACTOR_PRESET", "K_FACTOR", "N0", "EPSILON", "SIGMA",
    "RANK_BY", "OUTPUT_MARKERS", "OUTPUT_CSV", "OUTPUT_JSON",
]


class TestP2PParameterRegistration:
    def test_all_expected_params_present(self, provider):
        alg = _get_algorithm(provider, "p2p_analysis")
        param_names = [p.name() for p in alg.parameterDefinitions()]
        for expected in EXPECTED_P2P_PARAMS:
            assert expected in param_names, "Missing param: {} (have: {})".format(
                expected, sorted(param_names))

    def test_no_extra_params(self, provider):
        alg = _get_algorithm(provider, "p2p_analysis")
        param_names = set(p.name() for p in alg.parameterDefinitions())
        expected_set = set(EXPECTED_P2P_PARAMS)
        extra = param_names - expected_set
        assert not extra, "Unexpected extra params: {}".format(sorted(extra))

    def test_point_params_are_points(self, provider):
        from qgis.core import QgsProcessingParameterPoint
        alg = _get_algorithm(provider, "p2p_analysis")
        for name in ("TX_POINT", "RX_POINT"):
            param = alg.parameterDefinition(name)
            assert isinstance(param, QgsProcessingParameterPoint)

    def test_height_params_are_doubles(self, provider):
        from qgis.core import QgsProcessingParameterNumber
        alg = _get_algorithm(provider, "p2p_analysis")
        for name in ("TX_HEIGHT", "RX_HEIGHT"):
            param = alg.parameterDefinition(name)
            assert isinstance(param, QgsProcessingParameterNumber)


class TestCoverageParameterRegistration:
    def test_all_expected_params_present(self, provider):
        alg = _get_algorithm(provider, "coverage_analysis")
        param_names = [p.name() for p in alg.parameterDefinitions()]
        for expected in EXPECTED_COVERAGE_PARAMS:
            assert expected in param_names, "Missing param: {}".format(expected)

    def test_radius_param_has_bounds(self, provider):
        from qgis.core import QgsProcessingParameterNumber
        alg = _get_algorithm(provider, "coverage_analysis")
        radius = alg.parameterDefinition("RADIUS_KM")
        assert isinstance(radius, QgsProcessingParameterNumber)
        assert radius.minimum() == 1.0
        assert radius.maximum() == 500.0


class TestContourParameterRegistration:
    def test_all_expected_params_present(self, provider):
        alg = _get_algorithm(provider, "contour_lines")
        param_names = [p.name() for p in alg.parameterDefinitions()]
        for expected in EXPECTED_CONTOUR_PARAMS:
            assert expected in param_names, "Missing param: {}".format(expected)

    def test_extent_param_type(self, provider):
        from qgis.core import QgsProcessingParameterExtent
        alg = _get_algorithm(provider, "contour_lines")
        param = alg.parameterDefinition("AREA_OF_INTEREST")
        assert isinstance(param, QgsProcessingParameterExtent)

    def test_auth_config_param_type(self, provider):
        from qgis.core import QgsProcessingParameterAuthConfig
        alg = _get_algorithm(provider, "contour_lines")
        param = alg.parameterDefinition("PROXY_AUTH")
        assert isinstance(param, QgsProcessingParameterAuthConfig)
        assert param.flags() & QgsProcessingParameterAuthConfig.Flag.FlagOptional


class TestComparisonParameterRegistration:
    def test_algorithm_registers(self, provider):
        alg = _get_algorithm(provider, "coverage_comparison")
        param_names = [p.name() for p in alg.parameterDefinitions()]
        assert "DELTA_STYLE" in param_names
        assert "DELTA_THRESHOLD_DB" in param_names

    def test_delta_threshold_bounds(self, provider):
        from qgis.core import QgsProcessingParameterNumber
        alg = _get_algorithm(provider, "coverage_comparison")
        param = alg.parameterDefinition("DELTA_THRESHOLD_DB")
        assert isinstance(param, QgsProcessingParameterNumber)
        assert param.minimum() == 0.1


class TestBatchParameterRegistration:
    def test_all_expected_params_present(self, provider):
        alg = _get_algorithm(provider, "batch_p2p_analysis")
        param_names = [p.name() for p in alg.parameterDefinitions()]
        for expected in EXPECTED_BATCH_PARAMS:
            assert expected in param_names, "Missing param: {}".format(expected)

    def test_feature_source_params(self, provider):
        from qgis.core import QgsProcessingParameterFeatureSource
        alg = _get_algorithm(provider, "batch_p2p_analysis")
        for name in ("RX_LAYER", "TX_LAYER"):
            param = alg.parameterDefinition(name)
            assert isinstance(param, QgsProcessingParameterFeatureSource)