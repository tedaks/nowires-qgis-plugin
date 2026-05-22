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


Rule-based symbology for P2P Fresnel zone, line, and profile layers.
"""

from qgis.core import (
    QgsFillSymbol,
    QgsLineSymbol,
    QgsRuleBasedRenderer,
    QgsSymbol,
)

__all__ = [
    "apply_fresnel_polygon_symbology",
    "apply_fresnel_lines_symbology",
    "apply_profile_line_symbology",
]


def apply_fresnel_polygon_symbology(layer):
    """Apply rule-based symbology to the Fresnel zone polygon layer.

    Features:
      - type='fresnel_zone': full 1st Fresnel zone (cyan, semi-transparent)
      - type='fresnel_violation_band_60pct': 60% inner band (red, semi-transparent)
    """
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    renderer = QgsRuleBasedRenderer(symbol)
    root_rule = renderer.rootRule()

    f1_rule = root_rule.children()[0]
    f1_rule.setLabel("1st Fresnel Zone")
    f1_rule.setFilterExpression('"type" = \'fresnel_zone\'')
    f1_fill = QgsFillSymbol.createSimple(
        {"color": "0,255,255,80", "outline_color": "0,200,200,180", "outline_width": "0.4"}
    )
    f1_rule.setSymbol(f1_fill)

    band_rule = root_rule.children()[0].clone()
    band_rule.setLabel("60% Violation Band")
    band_rule.setFilterExpression('"type" = \'fresnel_violation_band_60pct\'')
    band_fill = QgsFillSymbol.createSimple(
        {"color": "255,60,60,100", "outline_color": "200,0,0,200", "outline_width": "0.5"}
    )
    band_rule.setSymbol(band_fill)
    root_rule.appendChild(band_rule)

    layer.setRenderer(renderer)
    layer.triggerRepaint()


def apply_fresnel_lines_symbology(layer):
    """Apply rule-based symbology to the Fresnel zone lines layer.

    Features:
      - type='terrain': terrain profile (brown)
      - type='los': line-of-sight (green dashed), blocked=True turns red
    """
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    renderer = QgsRuleBasedRenderer(symbol)
    root_rule = renderer.rootRule()

    terrain_rule = root_rule.children()[0]
    terrain_rule.setLabel("Terrain")
    terrain_rule.setFilterExpression('"type" = \'terrain\' AND "blocked" = 0')
    terrain_sym = QgsLineSymbol.createSimple(
        {"color": "139,105,20,255", "width": "1.5"}
    )
    terrain_rule.setSymbol(terrain_sym)

    terrain_blocked_rule = terrain_rule.clone()
    terrain_blocked_rule.setLabel("Terrain (LOS blocked)")
    terrain_blocked_rule.setFilterExpression('"type" = \'terrain\' AND "blocked" = 1')
    terrain_blocked_sym = QgsLineSymbol.createSimple(
        {"color": "200,50,50,255", "width": "1.5"}
    )
    terrain_blocked_rule.setSymbol(terrain_blocked_sym)
    root_rule.appendChild(terrain_blocked_rule)

    los_rule = terrain_rule.clone()
    los_rule.setLabel("Line of Sight")
    los_rule.setFilterExpression('"type" = \'los\'')
    los_sym = QgsLineSymbol.createSimple(
        {"color": "0,200,0,220", "width": "1.2", "style": "dash"}
    )
    los_rule.setSymbol(los_sym)
    root_rule.appendChild(los_rule)

    layer.setRenderer(renderer)
    layer.triggerRepaint()


def apply_profile_line_symbology(layer):
    """Apply symbology to the P2P profile link line layer.

    Colors the line by propagation mode:
      - mode=1 (LOS): green
      - mode=2 (Diffraction): orange
      - mode=3 (Tropospheric scatter): red
      - default: gray
    """
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    renderer = QgsRuleBasedRenderer(symbol)
    root_rule = renderer.rootRule()

    los_rule = root_rule.children()[0]
    los_rule.setLabel("LOS")
    los_rule.setFilterExpression('"mode" = 1')
    los_sym = QgsLineSymbol.createSimple(
        {"color": "0,200,0,255", "width": "2.0"}
    )
    los_rule.setSymbol(los_sym)

    diff_rule = los_rule.clone()
    diff_rule.setLabel("Diffraction")
    diff_rule.setFilterExpression('"mode" = 2')
    diff_sym = QgsLineSymbol.createSimple(
        {"color": "255,165,0,255", "width": "2.0"}
    )
    diff_rule.setSymbol(diff_sym)
    root_rule.appendChild(diff_rule)

    tropo_rule = los_rule.clone()
    tropo_rule.setLabel("Tropospheric Scatter")
    tropo_rule.setFilterExpression('"mode" = 3')
    tropo_sym = QgsLineSymbol.createSimple(
        {"color": "220,50,50,255", "width": "2.0"}
    )
    tropo_rule.setSymbol(tropo_sym)
    root_rule.appendChild(tropo_rule)

    other_rule = los_rule.clone()
    other_rule.setLabel("Other")
    other_rule.setFilterExpression('"mode" IS NULL OR "mode" NOT IN (1, 2, 3)')
    other_sym = QgsLineSymbol.createSimple(
        {"color": "160,160,160,255", "width": "2.0"}
    )
    other_rule.setSymbol(other_sym)
    root_rule.appendChild(other_rule)

    layer.setRenderer(renderer)
    layer.triggerRepaint()
