# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo
        email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/


Shared processing utilities for NoWires algorithms.
"""

from qgis.core import QgsProject, QgsProcessingContext


def queue_layer_for_loading(context, layer, name):
    if layer is None or not layer.isValid():
        return False
    if not (
        hasattr(context, "temporaryLayerStore")
        and hasattr(context, "addLayerToLoadOnCompletion")
    ):
        return False
    project = QgsProject.instance()
    context.temporaryLayerStore().addMapLayer(layer)
    context.addLayerToLoadOnCompletion(
        layer.id(), QgsProcessingContext.LayerDetails(name, project, name)
    )
    return True