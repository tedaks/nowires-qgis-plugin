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


Shared helpers for NoWires 3D scene support.
"""

import sys

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox, QMessageBox

from .base_algorithm import ENTRY_KEY_LAST_COVERAGE, ENTRY_KEY_LAST_DEM


SCENE_MODE_LOCAL = "local"
SCENE_MODE_GLOBE = "globe"
PROJECT_SCOPE = "NoWires"
CONTOUR_LAYER_KEY = "last_contour_layer_id"
VIEW_NAME_PREFIX = "NoWires 3D View"


class Windows3DFallbackDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3D View Not Available on Windows")
        self.setText(
            "Plugin-launched 3D view crashes QGIS on Windows due to a Qt/OpenGL conflict on Windows.\n\n"
            "You can still view your results in 3D manually:\n\n"
            "1. Go to View > 3D Map Views > New 3D Map View\n"
            "2. In the 3D view panel, click the wrench icon to configure terrain\n"
            "3. Set the DEM layer as the terrain elevation source\n\n"
            "The NoWires DEM and coverage layers will be highlighted in\n"
            "the layer panel so you can find them easily."
        )
        self.setIcon(QMessageBox.Icon.Warning)
        self.highlight_button = self.addButton(
            "Highlight Layers", QMessageBox.ButtonRole.AcceptRole
        )
        self.addButton("Close", QMessageBox.ButtonRole.RejectRole)

        try:
            cb = QCheckBox("Highlight NoWires layers in layer tree")
            cb.setChecked(True)
            self.setCheckBox(cb)
        except (AttributeError, TypeError):
            cb = None
        self.highlight_checkbox = cb


def highlight_nowires_layers(iface):
    """Select and expand NoWires DEM, coverage, and contour layers in layer tree."""
    try:
        project = QgsProject.instance()
        dem_id = project.readEntry(PROJECT_SCOPE, ENTRY_KEY_LAST_DEM)[0]
        coverage_id = project.readEntry(PROJECT_SCOPE, ENTRY_KEY_LAST_COVERAGE)[0]
        contour_id = project.readEntry("NoWires", "last_contour_layer_id")[0]

        root = project.layerTreeRoot()
        for layer_id in [dem_id, coverage_id, contour_id]:
            if not layer_id:
                continue
            layer = project.mapLayer(layer_id)
            if layer:
                tree_layer = root.findLayer(layer.id())
                if tree_layer:
                    tree_layer.setItemChecked(Qt.CheckState.Checked)
                    parent = tree_layer.parent()
                    if parent and parent != root:
                        parent.setExpanded(True)
    except Exception:
        pass


def remember_nowires_3d_layers(
    project, dem_layer=None, coverage_layer=None, contour_layer=None
):
    """Store the latest NoWires layers used for opening a 3D scene."""
    entries = {
        ENTRY_KEY_LAST_DEM: dem_layer.id() if dem_layer else "",
        ENTRY_KEY_LAST_COVERAGE: coverage_layer.id() if coverage_layer else "",
        CONTOUR_LAYER_KEY: contour_layer.id() if contour_layer else "",
    }
    for key, value in entries.items():
        if value:
            project.writeEntry(PROJECT_SCOPE, key, value)


def resolve_nowires_3d_layers(project):
    """Resolve the latest stored NoWires layer ids back to project layers."""
    layer_ids = {}
    for key in (ENTRY_KEY_LAST_DEM, ENTRY_KEY_LAST_COVERAGE, CONTOUR_LAYER_KEY):
        layer_id, ok = project.readEntry(PROJECT_SCOPE, key, "")
        layer_ids[key] = layer_id if ok else ""
    return {
        "dem_layer": project.mapLayer(layer_ids[ENTRY_KEY_LAST_DEM]),
        "coverage_layer": project.mapLayer(layer_ids[ENTRY_KEY_LAST_COVERAGE]),
        "contour_layer": project.mapLayer(layer_ids[CONTOUR_LAYER_KEY]),
    }


def _set_layer_visible(project, layer):
    """Ensure a layer is visible in the project layer tree when present."""
    if layer is None:
        return
    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None:
        node.setItemVisibilityChecked(True)


def configure_contours_for_3d(layer, elevation_field="ELEV"):
    """Apply terrain-aware elevation settings to contour output."""
    props = layer.elevationProperties()
    props.setClamping(Qgis.AltitudeClamping.Terrain)
    props.setBinding(Qgis.AltitudeBinding.Vertex)
    if hasattr(props, "setZOffsetExpression"):
        props.setZOffsetExpression('coalesce("{field}", 0)'.format(field=elevation_field))
    return layer


def _next_3d_view_name(iface):
    """Generate a unique 3D view name for the current QGIS session."""
    existing = []
    if hasattr(iface, "mapCanvases3D"):
        existing = iface.mapCanvases3D() or []
    return "{} {}".format(VIEW_NAME_PREFIX, len(existing) + 1)


def open_nowires_3d_view(iface, scene_mode=SCENE_MODE_LOCAL):
    """Create a new QGIS 3D map canvas using the latest NoWires layers."""
    is_windows = sys.platform == "win32"
    if is_windows:
        dialog = Windows3DFallbackDialog()
        dialog.exec()
        if dialog.clickedButton() == dialog.highlight_button:
            if dialog.highlight_checkbox and dialog.highlight_checkbox.isChecked():
                highlight_nowires_layers(iface)
        return None

    project = QgsProject.instance()
    layers = resolve_nowires_3d_layers(project)
    dem_layer = layers["dem_layer"]
    coverage_layer = layers["coverage_layer"]
    contour_layer = layers["contour_layer"]

    if dem_layer is None:
        iface.messageBar().pushWarning(
            "NoWires",
            "No DEM layer found for 3D. Run Coverage Analysis or Contour Lines first.",
        )
        return None

    if contour_layer is not None:
        configure_contours_for_3d(contour_layer, elevation_field="ELEV")
        _set_layer_visible(project, contour_layer)
    if coverage_layer is not None:
        _set_layer_visible(project, coverage_layer)
    _set_layer_visible(project, dem_layer)

    scene = (
        Qgis.SceneMode.Globe
        if scene_mode == SCENE_MODE_GLOBE
        else Qgis.SceneMode.Local
    )
    canvas = iface.createNewMapCanvas3D(_next_3d_view_name(iface), scene)

    if hasattr(project, "elevationProperties"):
        elevation_props = project.elevationProperties()
        if elevation_props is not None and hasattr(elevation_props, "setTerrainProvider"):
            try:
                from qgis.core import QgsRasterDemTerrainProvider
                _provider_cls = QgsRasterDemTerrainProvider
            except ImportError:
                return None
            provider = _provider_cls()
            provider.setLayer(dem_layer)
            elevation_props.setTerrainProvider(provider)

            settings = canvas.mapSettings()
            if hasattr(settings, "configureTerrainFromProject"):
                extent = (
                    iface.mapCanvas().fullExtent()
                    if hasattr(iface, "mapCanvas") and iface.mapCanvas() is not None
                    else dem_layer.extent()
                )
                settings.configureTerrainFromProject(elevation_props, extent)

    canvas.resetView()
    return canvas
