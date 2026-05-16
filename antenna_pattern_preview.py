# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Antenna pattern polar preview dialog.

Standalone QDialog for loading an antenna pattern CSV (angle_deg, gain_db)
and rendering it as a polar plot. Surfaced from the NoWires plugin menu so
non-RF users can sanity-check a pattern file before referencing it from a
P2P or Coverage run.

Rendering uses QPainter directly to avoid pulling in matplotlib at runtime.
"""
from __future__ import annotations

import logging
import math

from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from .antenna import _read_pattern_points

logger = logging.getLogger(__name__)

_RADIAL_LABEL_STEPS_DB = (0, -3, -6, -10, -20, -30)
_DEFAULT_MIN_DB = -40.0


def _normalize_to_max(points):
    """Re-base gains so 0 dB is the peak; return list of (angle, gain_db)."""
    if not points:
        return []
    peak = max(g for _, g in points)
    return [(a, g - peak) for a, g in points]


class _PolarPlot(QWidget):
    """Custom widget that paints a polar antenna pattern."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[tuple[float, float]] = []
        self._min_db = _DEFAULT_MIN_DB
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_points(self, points):
        self._points = _normalize_to_max(points)
        if self._points:
            self._min_db = min(min(g for _, g in self._points), _DEFAULT_MIN_DB)
        self.update()

    def paintEvent(self, event):  # noqa: N802 — Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))

        side = min(self.width(), self.height()) - 40
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r_max = side / 2.0

        self._draw_grid(painter, cx, cy, r_max)
        if self._points:
            self._draw_pattern(painter, cx, cy, r_max)

    def _db_to_radius(self, gain_db, r_max):
        # Clamp below min, map [_min_db..0] → [0..r_max] linearly.
        clamped = max(self._min_db, min(0.0, gain_db))
        return r_max * (1.0 - (clamped / self._min_db))

    def _draw_grid(self, painter, cx, cy, r_max):
        grid_pen = QPen(QColor("#cbd2d9"))
        grid_pen.setWidthF(1.0)
        painter.setPen(grid_pen)
        for db in _RADIAL_LABEL_STEPS_DB:
            if db < self._min_db:
                continue
            r = self._db_to_radius(db, r_max)
            painter.drawEllipse(QPointF(cx, cy), r, r)
        for deg in range(0, 360, 30):
            theta = math.radians(deg - 90)
            x = cx + r_max * math.cos(theta)
            y = cy + r_max * math.sin(theta)
            painter.drawLine(QPointF(cx, cy), QPointF(x, y))

        painter.setPen(QColor("#52606d"))
        font = QFont(painter.font())
        font.setPointSize(8)
        painter.setFont(font)
        for db in _RADIAL_LABEL_STEPS_DB:
            if db < self._min_db:
                continue
            r = self._db_to_radius(db, r_max)
            painter.drawText(QPointF(cx + 4, cy - r - 2), "{} dB".format(db))
        for deg in range(0, 360, 30):
            theta = math.radians(deg - 90)
            x = cx + (r_max + 14) * math.cos(theta)
            y = cy + (r_max + 14) * math.sin(theta) + 4
            painter.drawText(QPointF(x - 8, y), "{}°".format(deg))

    def _draw_pattern(self, painter, cx, cy, r_max):
        # Append the first point at the end so the curve closes for omni-ish patterns.
        wrapped = list(self._points)
        if wrapped[0][0] != (wrapped[-1][0] - 360) and wrapped[-1][0] < 360:
            wrapped.append((wrapped[0][0] + 360, wrapped[0][1]))
        poly = QPolygonF()
        for angle_deg, gain_db in wrapped:
            r = self._db_to_radius(gain_db, r_max)
            theta = math.radians(angle_deg - 90)
            poly.append(QPointF(cx + r * math.cos(theta), cy + r * math.sin(theta)))
        pen = QPen(QColor("#cc5500"))
        pen.setWidthF(2.0)
        painter.setPen(pen)
        painter.setBrush(QColor(204, 85, 0, 60))
        painter.drawPolygon(poly)


class AntennaPatternPreviewDialog(QDialog):
    """Dialog wrapping the polar plot widget plus a file-picker control."""

    def __init__(self, parent=None, initial_path: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("NoWires — Antenna Pattern Preview")
        self.resize(560, 600)
        self._label = QLabel("No pattern loaded.")
        self._plot = _PolarPlot(self)

        pick_btn = QPushButton("Load pattern CSV…")
        pick_btn.clicked.connect(self._on_pick)

        top = QHBoxLayout()
        top.addWidget(pick_btn)
        top.addStretch(1)
        top.addWidget(self._label)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._plot, stretch=1)

        if initial_path:
            self._load(initial_path)

    def _on_pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select antenna pattern CSV", "", "CSV files (*.csv)")
        if path:
            self._load(path)

    def _load(self, path: str):
        try:
            points = _read_pattern_points(path)
        except (OSError, ValueError) as exc:
            self._label.setText("Could not load pattern: {}".format(exc))
            self._plot.set_points([])
            logger.warning("Pattern preview load failed: %s", exc)
            return
        self._plot.set_points(points)
        self._label.setText("{} — {} points".format(path, len(points)))
