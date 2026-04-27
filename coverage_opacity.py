# -*- coding: utf-8 -*-
"""Live opacity adjustment for the latest coverage raster layer."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)
from qgis.core import QgsProject

COVERAGE_LAYER_PREFIX = "Coverage ("


def find_latest_coverage_layer():
    """Return the most recently added coverage raster layer, or None."""
    project = QgsProject.instance()

    layer_id, ok = project.readEntry("NoWires", "last_coverage_layer_id", "")
    if ok and layer_id:
        layer = project.mapLayer(layer_id)
        if layer is not None:
            return layer

    candidates = []
    for layer in project.mapLayers().values():
        if layer.name().startswith(COVERAGE_LAYER_PREFIX):
            candidates.append(layer)
    if not candidates:
        return None
    return candidates[-1]


class CoverageOpacityDialog(QDialog):
    """Non-modal dialog with a slider to adjust coverage layer opacity."""

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self._layer_id = layer.id()
        self.setWindowTitle("Coverage Opacity")
        self.setModal(False)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        label = QLabel("Coverage layer: {}".format(layer.name()), self)
        label.setWordWrap(True)
        layout.addWidget(label)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)

        self._pct_label = QLabel("100%", self)
        self._pct_label.setMinimumWidth(42)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(5)
        self._slider.setTickInterval(10)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        initial_opacity = int(round(layer.opacity() * 100))
        self._slider.setValue(initial_opacity)
        self._pct_label.setText("{}%".format(initial_opacity))

        self._slider.valueChanged.connect(self._on_slider_changed)

        slider_row.addWidget(self._slider)
        slider_row.addWidget(self._pct_label)
        layout.addLayout(slider_row)

    def _resolve_layer(self):
        layer = QgsProject.instance().mapLayer(self._layer_id)
        if layer is not None and layer.isValid():
            return layer
        return None

    def _on_slider_changed(self, value):
        self._pct_label.setText("{}%".format(value))
        layer = self._resolve_layer()
        if layer is None:
            self._slider.setEnabled(False)
            self._pct_label.setText("Layer removed")
            return
        layer.setOpacity(value / 100.0)
        layer.triggerRepaint()
        try:
            from qgis.utils import iface

            if iface is not None:
                iface.mapCanvas().refresh()
        except ImportError:
            pass
