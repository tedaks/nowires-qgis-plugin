# -*- coding: utf-8 -*-
"""Regression tests for coverage engine performance improvements."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
ENGINE_SOURCE = os.path.join(PLUGIN_DIR, "coverage_engine.py")


def _engine_source():
    with open(ENGINE_SOURCE, "r", encoding="utf-8") as handle:
        return handle.read()


def test_max_workers_uses_cpu_count():
    source = _engine_source()
    assert "os.cpu_count()" in source
    assert "_MAX_WORKERS = os.cpu_count()" in source


def test_no_hardcoded_chunk_size_constant():
    source = _engine_source()
    assert "_CHUNK_SIZE = 512" not in source


def test_dynamic_chunk_size_function():
    source = _engine_source()
    assert "def _dynamic_chunk_size(" in source
    assert "_MIN_CHUNK_SIZE" in source
    assert "_MAX_CHUNK_SIZE" in source


def test_windows_multiprocessing_enabled():
    source = _engine_source()
    assert "multiprocessing.freeze_support()" in source
    assert 'os_name != "nt"' not in source


def test_presample_elevations_function():
    source = _engine_source()
    assert "def _presample_elevations(" in source
    assert "sample_line_from_grid" in source


def test_sequential_path_uses_numba_presampling():
    source = _engine_source()
    assert "_HAS_NUMBA" in source
    assert "_presample_elevations" in source
    assert "compute_itm_p2p(" in source


def test_dynamic_chunk_size_used_in_coverage():
    source = _engine_source()
    assert "_dynamic_chunk_size(len(tasks))" in source
