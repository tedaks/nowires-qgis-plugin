# -*- coding: utf-8 -*-
"""Floating map-canvas legend for coverage analysis."""

from qgis.PyQt.QtCore import QEvent, Qt
from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .coverage_palette import build_legend_entries


LEGEND_OBJECT_NAME = "NoWiresCoverageLegend"


class CoverageLegendWidget(QFrame):
    """Floating legend widget anchored to the map canvas."""

    def __init__(self, canvas, rx_sensitivity_dbm):
        super().__init__(canvas)
        self._canvas = canvas
        self._rx_sensitivity_dbm = rx_sensitivity_dbm
        self.setObjectName(LEGEND_OBJECT_NAME)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet(
            """
            QFrame#NoWiresCoverageLegend {
                background-color: rgba(20, 24, 30, 220);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 8px;
            }
            QLabel {
                color: rgb(235, 240, 245);
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title = QLabel("Signal Legend", self)
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        for threshold_dbm, rgba, label in build_legend_entries():
            layout.addLayout(self._build_entry_row(threshold_dbm, rgba, label))

        footer = QLabel(
            "RX sensitivity: {:.0f} dBm".format(rx_sensitivity_dbm),
            self,
        )
        footer.setStyleSheet("color: rgba(225, 232, 240, 170); padding-top: 4px;")
        layout.addWidget(footer)

        self._canvas.installEventFilter(self)
        self.adjustSize()
        self._reposition()

    def _build_entry_row(self, threshold_dbm, rgba, label):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        swatch = QWidget(self)
        swatch.setFixedSize(16, 16)
        swatch.setStyleSheet(
            "background-color: rgba({r}, {g}, {b}, {a}); border-radius: 3px;".format(
                r=rgba[0], g=rgba[1], b=rgba[2], a=rgba[3]
            )
        )

        threshold = QLabel("\u2265 {:.0f} dBm".format(threshold_dbm), self)
        threshold.setMinimumWidth(74)

        name = QLabel(label, self)
        name.setStyleSheet("color: rgba(225, 232, 240, 170);")

        row.addWidget(swatch)
        row.addWidget(threshold)
        row.addStretch(1)
        row.addWidget(name)
        return row

    def eventFilter(self, watched, event):
        if watched is self._canvas and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._reposition()
        return super().eventFilter(watched, event)

    def _reposition(self):
        margin = 16
        self.adjustSize()
        x_pos = max(margin, self._canvas.width() - self.width() - margin)
        y_pos = margin
        self.move(x_pos, y_pos)

    def cleanup(self):
        self._canvas.removeEventFilter(self)


def remove_coverage_legend():
    """Remove the current coverage legend from the map canvas if present."""
    try:
        from qgis.utils import iface
    except ImportError:
        return

    if iface is None:
        return

    canvas = iface.mapCanvas()
    if canvas is None:
        return

    existing = canvas.findChild(QFrame, LEGEND_OBJECT_NAME)
    if existing is not None:
        if hasattr(existing, "cleanup"):
            existing.cleanup()
        existing.deleteLater()


def show_coverage_legend(rx_sensitivity_dbm):
    """Show the floating coverage legend on the current map canvas."""
    try:
        from qgis.utils import iface
    except ImportError:
        return None

    if iface is None:
        return None

    canvas = iface.mapCanvas()
    if canvas is None:
        return None

    remove_coverage_legend()
    legend = CoverageLegendWidget(canvas, rx_sensitivity_dbm)
    legend.show()
    legend.raise_()
    return legend
