# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import Qgis, QgsProcessingAlgorithm, QgsProject

ENTRY_KEY_LAST_DEM = "last_dem_layer_id"
ENTRY_KEY_LAST_COVERAGE = "last_coverage_layer_id"


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

    def postProcessAlgorithm(self, context, feedback):
        root = QgsProject.instance().layerTreeRoot()
        for layer_ids in (getattr(self, "_raster_layer_ids", []),
                         getattr(self, "_vector_layer_ids", [])):
            for layer_id in layer_ids:
                node = root.findLayer(layer_id)
                if node is not None:
                    parent = node.parent()
                    if parent is not None:
                        idx = parent.children().index(node)
                        parent.takeChildNode(node)
                        parent.insertChildNode(min(idx, len(parent.children())), node)
        for attr_name, entry_key in [
            ("_dem_layer_id", ENTRY_KEY_LAST_DEM),
            ("_coverage_layer_id", ENTRY_KEY_LAST_COVERAGE),
        ]:
            layer_id = getattr(self, attr_name, None)
            if layer_id is not None:
                QgsProject.instance().writeEntry("NoWires", entry_key, layer_id)
        return {}
