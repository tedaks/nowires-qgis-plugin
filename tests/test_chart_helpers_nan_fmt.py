# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

from NoWires.p2p.chart_helpers import _nan_safe_fmt


def test_nan_safe_fmt_returns_empty_for_nan():
    assert _nan_safe_fmt(float("nan"), ".2f") == ""


def test_nan_safe_fmt_returns_formatted_number():
    assert _nan_safe_fmt(3.14159, ".2f") == "3.14"


def test_nan_safe_fmt_handles_zero():
    assert _nan_safe_fmt(0.0, ".1f") == "0.0"
