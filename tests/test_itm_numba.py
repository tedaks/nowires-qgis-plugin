# -*- coding: utf-8 -*-
"""Regression tests for numba-accelerated ITM path."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
NUMBA_SOURCE = os.path.join(PLUGIN_DIR, "itm_numba.py")
ENGINE_SOURCE = os.path.join(PLUGIN_DIR, "coverage_engine.py")


def _text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def test_itm_numba_module_exists():
    assert os.path.isfile(NUMBA_SOURCE)


def test_itm_numba_has_graceful_fallback():
    source = _text(NUMBA_SOURCE)
    assert "_HAS_NUMBA" in source
    assert "try:" in source
    assert "from numba import njit" in source
    assert "except ImportError" in source


def test_itm_numba_has_compute_function():
    source = _text(NUMBA_SOURCE)
    assert "def compute_itm_p2p(" in source
    assert "_HAS_NUMBA" in source
    assert "pure-Python fallback" in source.lower() or "fallback" in source


def test_itm_numba_has_numba_entry_point():
    source = _text(NUMBA_SOURCE)
    assert "def nb_itm_p2p_loss(" in source


def test_itm_numba_has_fused_horizon_finder():
    source = _text(NUMBA_SOURCE)
    assert "_nb_find_horizons" in source


def test_itm_numba_has_fused_delta_h():
    source = _text(NUMBA_SOURCE)
    assert "_nb_compute_delta_h" in source


def test_itm_numba_has_fused_variability():
    source = _text(NUMBA_SOURCE)
    assert "_nb_variability" in source


def test_itm_numba_has_fused_longley_rice():
    source = _text(NUMBA_SOURCE)
    assert "_nb_diffraction_loss" in source
    assert "_nb_line_of_sight_loss" in source
    assert "_nb_troposcatter_loss" in source


def test_itm_numba_uses_njit_cache():
    source = _text(NUMBA_SOURCE)
    assert "@_njit(cache=True)" in source or "njit(cache=True)" in source


def test_coverage_engine_imports_numba_module():
    source = _text(ENGINE_SOURCE)
    assert "from .itm_numba import" in source


def test_coverage_engine_uses_compute_itm_p2p():
    source = _text(ENGINE_SOURCE)
    assert "compute_itm_p2p(" in source


def test_coverage_engine_itm_worker_uses_compute():
    source = _text(ENGINE_SOURCE)
    assert "result = compute_itm_p2p(" in source


def test_coverage_engine_radius_worker_uses_compute():
    source = _text(ENGINE_SOURCE)
    idx = source.find("_radius_worker")
    assert idx > 0
    radius_section = source[idx:]
    assert "compute_itm_p2p(" in radius_section


def test_coverage_engine_no_direct_itm_import():
    source = _text(ENGINE_SOURCE)
    assert "from .radio import build_pfl, itm_p2p_loss" not in source
