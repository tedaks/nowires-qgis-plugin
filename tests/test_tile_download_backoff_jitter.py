# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

from NoWires.tile_download_base import _backoff_seconds


class TestBackoffJitter:
    def test_backoff_bounds(self):
        seeds = [0, 42, 137]
        for seed in seeds:
            import random
            random.seed(seed)
            for attempt in range(4):
                result = _backoff_seconds(attempt)
                base = 2 ** attempt
                assert base <= result < base + 1, (
                    f"seed={seed}, attempt={attempt}: {result} not in [{base}, {base+1})"
                )

    def test_two_calls_differ(self):
        import random
        random.seed(1)
        a = _backoff_seconds(2)
        random.seed(2)
        b = _backoff_seconds(2)
        assert a != b, "Backoff should produce different values with different seeds"
