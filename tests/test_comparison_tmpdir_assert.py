# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from NoWires.comparison.reporting import resolve_output_paths


def test_resolve_output_paths_all_explicit_no_crash():
    out_a = "/tmp/test_a.tif"
    out_b = "/tmp/test_b.tif"
    out_delta = "/tmp/test_delta.tif"
    out_report = "/tmp/test_report.html"

    class FakeTmpMgr:
        def make_dir(self, *a, **kw):
            raise AssertionError("should not be called")

    result = resolve_output_paths(
        None, out_a, out_b, out_delta, out_report, FakeTmpMgr())
    assert result == (out_a, out_b, out_delta, out_report, None)