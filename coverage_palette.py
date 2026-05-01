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


Exact signal palette definitions.

Portions of this module are adapted from the tedaks/nowires web application
and were originally distributed under the MIT License. See NOTICE.md for
attribution details.
"""

SIGNAL_LEVELS = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    # Transparent by design: no-service cells should reveal the base map.
    (-120.0, (200, 40, 40, 0), "No service"),
]


def build_heatmap_stops():
    """Return the exact nowires palette sorted for the QGIS shader."""
    return sorted(SIGNAL_LEVELS, key=lambda item: item[0])


def apply_coverage_style(layer):
    """Apply a color ramp renderer based on signal level thresholds."""
    from qgis.PyQt.QtGui import QColor
    from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer

    provider = layer.dataProvider()
    entries = []
    for value, rgba, label in build_heatmap_stops():
        entry = QgsColorRampShader.ColorRampItem()
        entry.value = value
        entry.color = QColor(rgba[0], rgba[1], rgba[2], rgba[3])
        entry.label = "{} ({:.0f} dBm)".format(label, value)
        entries.append(entry)
    color_ramp_shader = QgsColorRampShader()
    color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
    color_ramp_shader.setColorRampItemList(entries)
    shader = QgsRasterShader()
    shader.setRasterShaderFunction(color_ramp_shader)
    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
    layer.setRenderer(renderer)
    layer.triggerRepaint()


def build_legend_entries():
    """Return legend entries in the original nowires top-down order."""
    return list(SIGNAL_LEVELS)
