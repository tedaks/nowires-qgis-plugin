# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from NoWires.report.export import _csv_safe


def test_leading_space_formula_injection():
    assert _csv_safe(" =1+1") == "'=1+1"


def test_leading_tab_formula_injection():
    assert _csv_safe("\t=1+1") == "'=1+1"


def test_leading_space_plus():
    assert _csv_safe(" +CMD(...)") == "'+CMD(...)"


def test_leading_space_at():
    assert _csv_safe(" @SUM(...)") == "'@SUM(...)"


def test_normal_value_unchanged():
    assert _csv_safe("hello") == "hello"


def test_existing_formula_prefix_still_caught():
    assert _csv_safe("=1+1") == "'=1+1"


def test_existing_minus_numeric_still_caught():
    assert _csv_safe("-1.5") == "-1.5"