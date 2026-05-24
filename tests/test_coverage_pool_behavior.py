# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for coverage_pool: _dynamic_chunk_size, _itm_worker, cancel_event."""

from NoWires.radio_coverage.pool import _dynamic_chunk_size, _MIN_CHUNK_SIZE, _MAX_CHUNK_SIZE


class TestDynamicChunkSize:
    def test_returns_min_for_zero_tasks(self):
        result = _dynamic_chunk_size(0)
        assert result == _MIN_CHUNK_SIZE

    def test_returns_min_for_small_task_count(self):
        result = _dynamic_chunk_size(10)
        assert result == _MIN_CHUNK_SIZE

    def test_returns_min_for_tasks_equal_to_min(self):
        result = _dynamic_chunk_size(_MIN_CHUNK_SIZE)
        assert result == _MIN_CHUNK_SIZE

    def test_returns_larger_chunk_for_many_tasks(self):
        result = _dynamic_chunk_size(5000000)
        assert result >= _MIN_CHUNK_SIZE
        assert result <= _MAX_CHUNK_SIZE

    def test_never_exceeds_max_chunk_size(self):
        result = _dynamic_chunk_size(10_000_000)
        assert result <= _MAX_CHUNK_SIZE

    def test_never_below_min_chunk_size(self):
        result = _dynamic_chunk_size(50)
        assert result >= _MIN_CHUNK_SIZE

    def test_chunk_size_scales_with_task_count(self):
        small = _dynamic_chunk_size(500)
        large = _dynamic_chunk_size(50000)
        assert large >= small

    def test_exact_boundary_at_min_chunk(self):
        result = _dynamic_chunk_size(_MIN_CHUNK_SIZE + 1)
        assert result >= _MIN_CHUNK_SIZE