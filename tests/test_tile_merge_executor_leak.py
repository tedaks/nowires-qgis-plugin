# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: ThreadPoolExecutor in tile_merge must be shut down properly."""

import os


def test_tile_merge_executor_is_managed():
    """Verify tile_merge.py does not create unmanaged ThreadPoolExecutor."""
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "tile_merge.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    assert "ThreadPoolExecutor" in source
    has_with = "with ThreadPoolExecutor" in source or "with concurrent.futures.ThreadPoolExecutor" in source
    has_shutdown_called = "shutdown()" in source
    assert has_with or has_shutdown_called, (
        "ThreadPoolExecutor must use 'with' statement or call shutdown()"
    )
    bare_executor_lines = [
        line for line in source.splitlines()
        if "ThreadPoolExecutor(max_workers=1)" in line
        and "with" not in line
    ]
    assert not bare_executor_lines, (
        "One-shot ThreadPoolExecutor without 'with' statement leaks threads"
    )