# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for batch/params.py — parameter constants and registration."""

import pytest

try:
    from qgis.core import QgsProcessingParameterEnum, QgsProcessingParameterNumber
    _HAS_QGIS = bool(__import__("os").environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False


class _FakeAlgorithm:
    def __init__(self):
        self.params = []

    def addParameter(self, param):
        self.params.append(param)

    def __getattr__(self, name):
        if name.isupper():
            return name
        raise AttributeError(name)


@pytest.fixture
def fake_alg():
    return _FakeAlgorithm()


# --- Constant tests (no QGIS needed) ---

def test_mode_options_are_two_entry_list():
    from NoWires.batch.params import BATCH_MODE_OPTIONS
    assert len(BATCH_MODE_OPTIONS) == 2
    assert "One-to-Many" in BATCH_MODE_OPTIONS[0]
    assert "Many-to-One" in BATCH_MODE_OPTIONS[1]


def test_rank_by_options_are_three_entry_list():
    from NoWires.batch.params import RANK_BY_OPTIONS
    assert len(RANK_BY_OPTIONS) == 3
    assert "margin" in RANK_BY_OPTIONS[0]
    assert "loss" in RANK_BY_OPTIONS[1]
    assert "Clearance" in RANK_BY_OPTIONS[2]


def test_batch_param_constants_self_reference():
    from NoWires.batch.params import BATCH_PARAM_CONSTANTS
    for key, value in BATCH_PARAM_CONSTANTS.items():
        assert key == value


def test_batch_param_constants_covers_all_expected_keys():
    from NoWires.batch.params import BATCH_PARAM_CONSTANTS
    expected = {"MODE", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "POLARIZATION",
                "CLIMATE", "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT",
                "RANK_BY", "OUTPUT_MARKERS", "OUTPUT_CSV", "OUTPUT_JSON"}
    for key in expected:
        assert key in BATCH_PARAM_CONSTANTS


def test_parameter_name_strings_are_documented_in_all():
    from NoWires.batch import params as mod
    public_names = {n for n in dir(mod) if n.isupper() and not n.startswith("_")}
    for name in ["MODE", "FREQ_MHZ", "POLARIZATION", "CLIMATE", "RANK_BY"]:
        assert name in public_names


# --- Parameter registration tests (QGIS needed) ---

@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_batch_params_registers_mode_param(fake_alg):
    from NoWires.batch.params import add_batch_params
    add_batch_params(fake_alg)
    names = {p.name() for p in fake_alg.params}
    assert "MODE" in names


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_batch_params_registers_link_params(fake_alg):
    from NoWires.batch.params import add_batch_params
    add_batch_params(fake_alg)
    names = {p.name() for p in fake_alg.params}
    for expected in ("TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "POLARIZATION", "CLIMATE",
                     "TIME_PCT", "LOCATION_PCT", "SITUATION_PCT"):
        assert expected in names, "Missing param: {}".format(expected)


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_batch_params_registers_antenna_params(fake_alg):
    from NoWires.batch.params import add_batch_params
    add_batch_params(fake_alg)
    names = {p.name() for p in fake_alg.params}
    for expected in ("TX_ANTENNA_PRESET", "TX_ANTENNA_AZ", "TX_FRONT_BACK_DB",
                     "RX_ANTENNA_PRESET", "RX_ANTENNA_AZ", "RX_FRONT_BACK_DB"):
        assert expected in names, "Missing param: {}".format(expected)


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_add_batch_params_registers_output_params(fake_alg):
    from NoWires.batch.params import add_batch_params
    add_batch_params(fake_alg)
    names = {p.name() for p in fake_alg.params}
    for expected in ("RANK_BY", "OUTPUT_MARKERS", "OUTPUT_CSV", "OUTPUT_JSON"):
        assert expected in names, "Missing param: {}".format(expected)


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_freq_mhz_has_correct_default_and_bounds(fake_alg):
    from NoWires.batch.params import add_batch_params
    from NoWires.defaults import DEFAULT_FREQ_MHZ
    from NoWires.radio import ITM_MIN_FREQUENCY_MHZ, ITM_MAX_FREQUENCY_MHZ

    add_batch_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "FREQ_MHZ")
    assert isinstance(param, QgsProcessingParameterNumber)
    assert param.defaultValue() == DEFAULT_FREQ_MHZ
    assert param.minimum() == ITM_MIN_FREQUENCY_MHZ
    assert param.maximum() == ITM_MAX_FREQUENCY_MHZ


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_tx_height_has_correct_default_and_bounds(fake_alg):
    from NoWires.batch.params import add_batch_params
    from NoWires.defaults import DEFAULT_TX_HEIGHT_M
    from NoWires.radio import ITM_MIN_TERMINAL_HEIGHT_M, ITM_MAX_TERMINAL_HEIGHT_M

    add_batch_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "TX_HEIGHT")
    assert isinstance(param, QgsProcessingParameterNumber)
    assert param.defaultValue() == DEFAULT_TX_HEIGHT_M
    assert param.minimum() == ITM_MIN_TERMINAL_HEIGHT_M
    assert param.maximum() == ITM_MAX_TERMINAL_HEIGHT_M


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_polarization_is_enum_with_default_vertical(fake_alg):
    from NoWires.batch.params import add_batch_params

    add_batch_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "POLARIZATION")
    assert isinstance(param, QgsProcessingParameterEnum)
    assert param.options() == ["Horizontal", "Vertical"]
    assert param.defaultValue() == 1


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_climate_has_enum_and_defaults(fake_alg):
    from NoWires.batch.params import add_batch_params
    from NoWires.constants import CLIMATE_OPTIONS

    add_batch_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "CLIMATE")
    assert isinstance(param, QgsProcessingParameterEnum)
    assert param.options() == CLIMATE_OPTIONS
    assert param.defaultValue() == 1


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_rank_by_is_enum_with_default_zero(fake_alg):
    from NoWires.batch.params import add_batch_params
    from NoWires.batch.params import RANK_BY_OPTIONS

    add_batch_params(fake_alg)
    param = next(p for p in fake_alg.params if p.name() == "RANK_BY")
    assert isinstance(param, QgsProcessingParameterEnum)
    assert param.options() == RANK_BY_OPTIONS
    assert param.defaultValue() == 0


@pytest.mark.skipif(not _HAS_QGIS, reason="QGIS not available")
def test_pct_params_have_same_min_max(fake_alg):
    from NoWires.batch.params import add_batch_params

    add_batch_params(fake_alg)
    for name in ("TIME_PCT", "LOCATION_PCT", "SITUATION_PCT"):
        param = next(p for p in fake_alg.params if p.name() == name)
        assert isinstance(param, QgsProcessingParameterNumber)
        assert param.minimum() == 0.01
        assert param.maximum() == 99.99
