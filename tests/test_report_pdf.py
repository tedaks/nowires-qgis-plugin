# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the PDF report writer.

The writer is split into two paths: a no-Qt fallback that logs and returns
False, and a real Qt path that writes a PDF file. The Qt path runs only in
the qgis_integration suite where a real QGIS/Qt runtime is available.
"""

import os
import sys

import pytest

from NoWires.report.pdf import write_report_pdf


_PAYLOAD = {
    "status": {"summary": "Smoke"},
    "geometry": {"tx_lat": 47.0, "tx_lon": -122.0},
}


def test_write_report_pdf_returns_false_when_qt_unavailable(tmp_path, monkeypatch):
    """If Qt imports fail, the writer logs and returns False — never raises."""
    # Simulate Qt unavailable by injecting an ImportError sentinel into the
    # qgis.PyQt.QtPrintSupport module slot.
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtPrintSupport", None)
    out = tmp_path / "r.pdf"
    result = write_report_pdf(out, _PAYLOAD, title="Test")
    assert result is False
    assert not out.exists()


_HAS_QT = bool(os.environ.get("QGIS_PREFIX_PATH"))


@pytest.mark.qgis_integration
@pytest.mark.skipif(not _HAS_QT, reason="Requires Qt6 print support")
def test_write_report_pdf_produces_pdf(qgis_app, tmp_path):
    out = tmp_path / "smoke.pdf"
    result = write_report_pdf(out, _PAYLOAD, title="Smoke")
    assert result is True
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"%PDF-")
    assert b"%%EOF" in data[-1024:]
