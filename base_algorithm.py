from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import Qgis, QgsProcessingAlgorithm, QgsProject


def install_constants(cls, names_or_dict):
    if isinstance(names_or_dict, dict):
        items = names_or_dict.items()
    else:
        items = ((n, n) for n in names_or_dict)
    for key, value in items:
        setattr(cls, key, value)


class NoWiresAlgorithm(QgsProcessingAlgorithm):
    GROUP_NAME = "Radio Propagation"
    GROUP_ID = "radio_propagation"

    def flags(self):
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def group(self):
        return self.tr(self.GROUP_NAME)

    def groupId(self):
        return self.GROUP_ID

    def postProcessAlgorithm(self, context, feedback):
        root = QgsProject.instance().layerTreeRoot()
        for layer_id in getattr(self, "_raster_layer_ids", []):
            node = root.findLayer(layer_id)
            if node is not None:
                clone = node.clone()
                parent = node.parent()
                parent.removeChildNode(node)
                parent.insertChildNode(0, clone)
        return {}