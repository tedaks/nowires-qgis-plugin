# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""PDF report writer.

Renders the same HTML document used by ``write_report_html`` into a printable
PDF via Qt's ``QTextDocument`` + ``QPrinter``. Kept in a dedicated module so
that ``report_export.py`` stays Qt-free for non-QGIS environments.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .report_export import build_html_document

logger = logging.getLogger(__name__)


def write_report_pdf(path, payload, title) -> bool:
    """Write a PDF report. Returns True on success, False if Qt is unavailable.

    Requires Qt6 / PyQt6 (bundled with QGIS 4). Imports are deferred so this
    module can be imported in environments where Qt isn't installed; in that
    case the function logs a warning and returns False rather than raising.
    """
    try:
        from qgis.PyQt.QtCore import QMarginsF
        from qgis.PyQt.QtGui import QPageLayout, QPageSize, QTextDocument
        from qgis.PyQt.QtPrintSupport import QPrinter
    except ImportError as exc:
        logger.warning("PDF report skipped — Qt print-support not available: %s", exc)
        return False

    document = QTextDocument()
    document.setHtml(build_html_document(payload, title))

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(Path(path)))
    # Qt6 QPageLayout requires (pageSize, orientation, margins, units, minMargins).
    layout = QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Portrait,
        QMarginsF(15, 15, 15, 15),  # 15 mm margins
        QPageLayout.Unit.Millimeter,
    )
    printer.setPageLayout(layout)

    # Qt6 renamed QTextDocument.print_ → print; keep both for safety.
    if hasattr(document, "print"):
        document.print(printer)
    else:
        document.print_(printer)
    return True
