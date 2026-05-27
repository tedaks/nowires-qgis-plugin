# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: antenna pattern CSV reader must enforce MAX_PATTERN_ROWS cap."""

import csv
import os
import tempfile

from NoWires.antenna import MAX_PATTERN_ROWS, _read_pattern_points, clear_pattern_cache


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for angle, gain in rows:
            writer.writerow([str(angle), str(gain)])


class TestAntennaPatternRowCap:
    def setup_method(self):
        clear_pattern_cache()

    def test_truncates_large_file_to_max_rows(self, caplog):
        rows = [(float(i) * 0.1, -3.0) for i in range(MAX_PATTERN_ROWS + 400)]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False,
        ) as tmp:
            path = tmp.name
            _write_csv(path, rows)

        try:
            result = _read_pattern_points(path)
            assert len(result) == MAX_PATTERN_ROWS
            assert "exceeds" in caplog.text
            assert "truncating" in caplog.text
        finally:
            os.unlink(path)

    def test_under_limit_not_truncated(self):
        rows = [(float(i) * 1.0, -3.0) for i in range(360)]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False,
        ) as tmp:
            path = tmp.name
            _write_csv(path, rows)

        try:
            result = _read_pattern_points(path)
            assert len(result) == 360
        finally:
            os.unlink(path)

    def test_max_pattern_rows_constant_defined(self):
        assert MAX_PATTERN_ROWS == 3600
