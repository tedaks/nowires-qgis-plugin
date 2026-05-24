# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test ImportError guard in write_report_pdf when QtPrintSupport is unavailable."""

from unittest import mock


def test_write_report_pdf_returns_false_on_import_error():
    with mock.patch.dict("sys.modules", clear=False):
        with mock.patch(
            "NoWires.report.pdf.QTextDocument",
            create=True,
            side_effect=ImportError("no Qt print support"),
        ):
            from NoWires.report.pdf import write_report_pdf
            result = write_report_pdf("/tmp/test.pdf", {"title": "Test"}, "Test Report")
            assert result is False
