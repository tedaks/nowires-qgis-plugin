# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for CSV formula-injection guards.

csv_safe strips unicode whitespace (including regular space) before checking
for formula trigger characters.  Leading-space-plus-formula triggers the
quote guard so leading whitespace is preserved in the guarded output.
"""
from NoWires.sanitizers import csv_safe


def test_leading_space_is_preserved():
    # Leading space is preserved in the output, formula guard applied
    assert csv_safe(" =1+1") == "' =1+1"


def test_leading_space_plus_preserved():
    assert csv_safe(" +CMD(...)") == "' +CMD(...)"


def test_leading_space_at_preserved():
    assert csv_safe(" @SUM(...)") == "' @SUM(...)"


def test_leading_tab_formula_injection():
    assert csv_safe("	=1+1") == "'\t=1+1"


def test_normal_value_unchanged():
    assert csv_safe("hello") == "hello"


def test_existing_formula_prefix_still_caught():
    assert csv_safe("=1+1") == "'=1+1"


def test_existing_minus_numeric_still_caught():
    assert csv_safe("-1.5") == "-1.5"
