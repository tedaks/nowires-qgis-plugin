# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
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

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingLayerPostProcessorInterface,
    QgsProject,
)


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


class _DestinationPostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Captures the loaded layer's id and runs a styler callback.

    Hold a reference (e.g. on the algorithm instance) until the algorithm
    finishes — QGIS only stores a raw pointer, so a GC'd Python wrapper
    crashes the runner.
    """

    def __init__(self, styler=None):
        super().__init__()
        self._styler = styler
        self.layer_id = None

    def postProcessLayer(self, layer, context, feedback):
        if layer is None:
            return
        self.layer_id = layer.id()
        if self._styler is None:
            return
        try:
            self._styler(layer)
        except Exception as exc:  # pragma: no cover - defensive
            if feedback is not None:
                feedback.pushWarning(
                    "Layer post-processor error: {}".format(exc))


def register_destination_layer(context, path, name, styler=None):
    """Hook into QGIS's auto-load of a destination output to set a custom
    layer name and run a styler post-processor on the loaded layer.

    Use this instead of ``queue_layer_for_loading`` whenever the algorithm
    declares the path via ``QgsProcessingParameterRasterDestination`` or
    ``QgsProcessingParameterVectorDestination``. Calling both leads to two
    competing load-on-completion entries for the same file and produces the
    QGIS warning "The following layers were not correctly generated".

    Returns the post-processor instance (read ``.layer_id`` after completion)
    or ``None`` when QGIS has no auto-load entry for *path* (e.g. the user
    chose "Skip output"); in that case the caller should fall back to
    ``queue_layer_for_loading``.
    """
    if not (
        hasattr(context, "willLoadLayerOnCompletion")
        and hasattr(context, "layerToLoadOnCompletionDetails")
    ):
        return None
    try:
        if not context.willLoadLayerOnCompletion(path):
            return None
    except Exception:
        return None
    details = context.layerToLoadOnCompletionDetails(path)
    if details is None:
        return None
    details.name = name
    pp = _DestinationPostProcessor(styler=styler)
    details.setPostProcessor(pp)
    return pp
