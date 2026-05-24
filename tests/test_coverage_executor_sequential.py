# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for _coverage_executor sequential mode and chunk sizing."""


from radio_coverage.pool import _dynamic_chunk_size, _MIN_CHUNK_SIZE, _MAX_CHUNK_SIZE


class TestDynamicChunkSize:
    def test_returns_positive_integer(self):
        size = _dynamic_chunk_size(1000)
        assert isinstance(size, int)
        assert size > 0

    def test_small_task_count_returns_min_chunk(self):
        size = _dynamic_chunk_size(10)
        assert size == _MIN_CHUNK_SIZE

    def test_large_task_count_gives_larger_chunks(self):
        size_small = _dynamic_chunk_size(100)
        size_large = _dynamic_chunk_size(100000)
        assert size_large >= size_small

    def test_never_below_min_chunk_size(self):
        for n in [1, 5, 10, 50, 64]:
            size = _dynamic_chunk_size(n)
            assert size >= _MIN_CHUNK_SIZE

    def test_never_above_max_chunk_size(self):
        size = _dynamic_chunk_size(10_000_000)
        assert size <= _MAX_CHUNK_SIZE