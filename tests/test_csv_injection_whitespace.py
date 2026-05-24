# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for CSV formula-injection guards.

M8/N21: csv_safe now only strips tab/CR (not spaces) before checking for
formula prefixes.  A leading space is NOT a formula-injection vector —
spreadsheets treat " =1+1" as literal text, not a formula.
"""
from NoWires.sanitizers import csv_safe


def test_leading_space_is_preserved():
    # A leading space prevents formula injection in spreadsheets
    assert csv_safe(" =1+1") == " =1+1"


def test_leading_space_plus_preserved():
    assert csv_safe(" +CMD(...)") == " +CMD(...)"


def test_leading_space_at_preserved():
    assert csv_safe(" @SUM(...)") == " @SUM(...)"


def test_leading_tab_formula_injection():
    assert csv_safe("	=1+1") == "'=1+1"


def test_normal_value_unchanged():
    assert csv_safe("hello") == "hello"


def test_existing_formula_prefix_still_caught():
    assert csv_safe("=1+1") == "'=1+1"


def test_existing_minus_numeric_still_caught():
    assert csv_safe("-1.5") == "-1.5"
