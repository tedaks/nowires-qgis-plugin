# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for coverage engine performance improvements."""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
ENGINE_SOURCE = os.path.join(PLUGIN_DIR, "coverage_engine.py")
POOL_SOURCE = os.path.join(PLUGIN_DIR, "coverage_pool.py")


def _engine_source():
    parts = []
    for path in (ENGINE_SOURCE, POOL_SOURCE):
        with open(path, "r", encoding="utf-8") as handle:
            parts.append(handle.read())
    return "\n".join(parts)


def test_max_workers_uses_cpu_count():
    source = _engine_source()
    assert "os.cpu_count()" in source
    assert "_MAX_WORKERS = min(os.cpu_count() or 1, 16)" in source


def test_no_hardcoded_chunk_size_constant():
    source = _engine_source()
    assert "_CHUNK_SIZE = 512" not in source


def test_dynamic_chunk_size_function():
    source = _engine_source()
    assert "def _dynamic_chunk_size(" in source
    assert "_MIN_CHUNK_SIZE" in source
    assert "_MAX_CHUNK_SIZE" in source


def test_didactic_chunk_size_used_in_coverage():
    source = _engine_source()
    assert "_dynamic_chunk_size(len(tasks))" in source


def test_windows_multiprocessing_disabled():
    source = _engine_source()
    assert 'os_name == "nt"' in source


def test_process_pool_executor_used():
    source = _engine_source()
    assert "ProcessPoolExecutor" in source


def test_thread_pool_not_used():
    source = _engine_source()
    assert "ThreadPoolExecutor" not in source


def test_sequential_fallback_exists():
    source = _engine_source()
    assert "use_mp" in source or "use_multiprocessing" in source
