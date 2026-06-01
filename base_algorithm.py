# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis, QgsLayerTreeGroup, QgsProcessingAlgorithm, QgsProject

ENTRY_KEY_LAST_DEM = "last_dem_layer_id"
ENTRY_KEY_LAST_COVERAGE = "last_coverage_layer_id"


def _open_report(path):
    from qgis.PyQt.QtGui import QDesktopServices
    from qgis.PyQt.QtCore import QUrl
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def install_constants(cls, names_or_dict):
    """Install string constants as class attributes for QgsProcessingAlgorithm.

    QGIS processing algorithms expose parameter/output names as class
    attributes (e.g. ``self.OUTPUT_RASTER``). This helper installs them
    from a dict or iterable of names, avoiding repetitive manual declarations.
    """
    if isinstance(names_or_dict, dict):
        items: list[tuple[str, str]] = list(names_or_dict.items())
    else:
        items = [(n, n) for n in names_or_dict]
    for key, value in items:
        setattr(cls, key, value)


class NoWiresAlgorithm(QgsProcessingAlgorithm):
    GROUP_NAME = "Radio Propagation"
    GROUP_ID = "radio_propagation"

    # Subclasses override to True to opt their processAlgorithm() into running
    # off the main thread via QgsProcessingAlgRunnerTask. Heavy-compute
    # algorithms (coverage, batch, comparison) opt in so the QGIS UI stays
    # responsive; quick algorithms keep NoThreading for simplicity.
    ALLOW_THREADING = False

    def flags(self):
        f = super().flags()
        if not self.ALLOW_THREADING:
            f |= Qgis.ProcessingAlgorithmFlag.NoThreading
        return f

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def group(self):
        return self.tr(self.GROUP_NAME)

    def groupId(self):
        return self.GROUP_ID

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "logo.png"))

    def shortHelpString(self):
        return self.tr(
            "Radio propagation analysis using the Irregular Terrain Model (ITM). "
            "See the NoWires User's Guide for detailed usage instructions."
        )

    def postProcessAlgorithm(self, context, feedback):
        project = context.project() if context.project() is not None else QgsProject.instance()
        root = project.layerTreeRoot()
        group_name = getattr(self, "_layer_tree_group_name", None)
        group = None
        if group_name:
            for child in root.children():
                if (isinstance(child, QgsLayerTreeGroup)
                        and child.name() == group_name):
                    group = child
                    break
            if group is None:
                group = root.addGroup(group_name)
        for layer_ids in (getattr(self, "_raster_layer_ids", []),
                         getattr(self, "_vector_layer_ids", [])):
            for layer_id in layer_ids:
                node = root.findLayer(layer_id)
                if node is None:
                    continue
                target = group if group is not None else node.parent()
                if target is not None and node.parent() is not target:
                    src_parent = node.parent()
                    if src_parent is not None:
                        src_parent.takeChildNode(node)
                    target.insertChildNode(0, node)
        for attr_name, entry_key in [
            ("_dem_layer_id", ENTRY_KEY_LAST_DEM),
            ("_coverage_layer_id", ENTRY_KEY_LAST_COVERAGE),
        ]:
            layer_id = getattr(self, attr_name, None)
            if layer_id is not None:
                project.writeEntry("NoWires", entry_key, layer_id)
        summary = getattr(self, "_run_summary", None)
        if summary is not None:
            try:
                from qgis.utils import iface
                from qgis.PyQt.QtWidgets import QAction
                report_path = summary.get("report_html_path")
                msg = summary.get("text", "NoWires analysis complete.")
                duration = summary.get("duration", 0.0)
                if duration > 0:
                    msg += " ({:.1f} s)".format(duration)
                widget = iface.messageBar().createMessage("NoWires", msg)
                if report_path:
                    open_action = QAction("View report", widget)
                    open_action.triggered.connect(
                        lambda checked=False, path=report_path: _open_report(path))
                    widget.addAction(open_action)
                iface.messageBar().pushWidget(widget, Qgis.MessageLevel.Info, duration=8)
            except Exception:
                pass
        return {}
