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
        copyright            : (C) 2026 Daniel Hulshof Saint Martin
                                Adaptations (C) 2026 Bortre Tenamo
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


Rule-based renderer and labeling for contour line layers.
"""

from qgis.core import (
    Qgis,
    QgsPalLayerSettings,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsSymbolLayerReference,
    QgsTextFormat,
    QgsTextMaskSettings,
    QgsVectorLayerSimpleLabeling,
)


def apply_contour_symbology(layer, color, interval):
    """Apply rule-based renderer and index-contour labels to *layer*."""
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    renderer = QgsRuleBasedRenderer(symbol)
    root_rule = renderer.rootRule()

    index_rule = root_rule.children()[0]
    index_rule.setLabel("Index Contour")
    index_rule.setFilterExpression(
        '"ELEV" % {itv} < 0.01 OR "ELEV" % {itv} > {itv} - 0.01'.format(
            itv=interval * 5
        )
    )
    index_rule.symbol().setColor(color)
    index_rule.symbol().setWidth(0.5)

    normal_rule = root_rule.children()[0].clone()
    normal_rule.setLabel("Normal Contour")
    normal_rule.setFilterExpression("ELSE")
    normal_rule.symbol().setColor(color)
    normal_rule.symbol().setWidth(0.25)
    root_rule.appendChild(normal_rule)

    layer.setRenderer(renderer)
    layer.triggerRepaint()

    mask = QgsTextMaskSettings()
    mask.setSize(2)
    index_contour_rule = root_rule.children()[0]
    mask.setMaskedSymbolLayers(
        [
            QgsSymbolLayerReference(
                layer.id(),
                index_contour_rule.symbol().symbolLayer(0).id(),
            )
        ]
    )
    mask.setEnabled(True)

    text_format = QgsTextFormat()
    text_format.setSize(10)
    text_format.setColor(color)
    text_format.setMask(mask)

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = (
        'CASE WHEN "ELEV" % {itv} < 0.01 OR "ELEV" % {itv} > {itv} - 0.01'
        " THEN \"ELEV\" ELSE '' END"
    ).format(itv=interval * 5)
    label_settings.enabled = True
    label_settings.drawLabels = True
    label_settings.repeatDistance = 50
    label_settings.isExpression = True
    label_settings.placement = Qgis.LabelPlacement.Line
    label_settings.placementFlags = Qgis.LabelLinePlacementFlag.OnLine

    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
    layer.triggerRepaint()