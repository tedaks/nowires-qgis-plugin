# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for _csv_safe formula-injection character coverage (v1.6.2).

Before the fix, _csv_safe only guarded against =, +, @, and numeric-leading
dash. Some spreadsheet applications also interpret en-dash (U+2013),
minus sign (U+2212), and Unicode whitespace as formula triggers.
"""

import pytest

CSV_SAFE_SOURCES = [
    ("\N{EN DASH}1+1", "en-dash (U+2013)"),
    ("\N{MINUS SIGN}1+1", "minus sign (U+2212)"),
    ("\N{IDEOGRAPHIC SPACE}=1+1", "ideographic space (U+3000)"),
    ("\N{EM SPACE}=1+1", "em space (U+2003)"),
    ("\N{EN SPACE}=1+1", "en space (U+2002)"),
    ("\N{ZERO WIDTH NO-BREAK SPACE}=1+1", "zero-width no-break space (U+FEFF)"),
]


@pytest.mark.parametrize(("payload", "_label"), CSV_SAFE_SOURCES)
def test_formula_trigger_chars_are_sanitized(payload, _label):
    """Rows starting with formula-trigger characters must be escaped."""
    from NoWires.report.export import _csv_safe

    result = _csv_safe(payload)
    assert result.startswith("'"), (
        "_{}_ payload {!r} was not escaped; result was {!r}".format(
            _label, payload, result
        )
    )


def test_ordinary_strings_untouched():
    """Ordinary safe values must round-trip."""
    from NoWires.report.export import _csv_safe

    for value in ("hello", "42.0", "-12.3", "line 1"):
        assert _csv_safe(value) == value


def test_leading_lstrip_still_works():
    """Leading whitespace stripping before formula check must still work."""
    from NoWires.report.export import _csv_safe

    result = _csv_safe("\t=1+1")
    assert result.startswith("'")
