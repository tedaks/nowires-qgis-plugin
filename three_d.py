# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
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

 Licensed under the MIT License; see the LICENSE file for the full text.


Shared helpers for NoWires 3D scene support.
"""

import logging
import sys

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox, QMessageBox

from NoWires.base_algorithm import ENTRY_KEY_LAST_COVERAGE, ENTRY_KEY_LAST_DEM


logger = logging.getLogger(__name__)

SCENE_MODE_LOCAL = "local"
SCENE_MODE_GLOBE = "globe"
PROJECT_SCOPE = "NoWires"
VIEW_NAME_PREFIX = "NoWires 3D View"


class Windows3DFallbackDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3D View Not Available on Windows")
        self.setText(
            "Plugin-launched 3D view crashes QGIS on Windows due to "
            "a Qt/OpenGL conflict on Windows.\n\n"
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


def highlight_nowires_layers(iface, project=None):
    """Select and expand NoWires DEM and coverage layers in layer tree."""
    try:
        if project is None:
            project = QgsProject.instance()
        dem_id = project.readEntry(PROJECT_SCOPE, ENTRY_KEY_LAST_DEM)[0]
        coverage_id = project.readEntry(PROJECT_SCOPE, ENTRY_KEY_LAST_COVERAGE)[0]

        root = project.layerTreeRoot()
        for layer_id in [dem_id, coverage_id]:
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
    except Exception as exc:
        logger.debug("layer tree highlight: %s", exc)


def remember_nowires_3d_layers(
    project, dem_layer=None, coverage_layer=None
):
    """Store the latest NoWires layers used for opening a 3D scene."""
    if project is None:
        return
    entries = {
        ENTRY_KEY_LAST_DEM: dem_layer.id() if dem_layer else "",
        ENTRY_KEY_LAST_COVERAGE: coverage_layer.id() if coverage_layer else "",
    }
    for key, value in entries.items():
        if value:
            project.writeEntry(PROJECT_SCOPE, key, value)


def resolve_nowires_3d_layers(project):
    """Resolve the latest stored NoWires layer ids back to project layers."""
    layer_ids = {}
    for key in (ENTRY_KEY_LAST_DEM, ENTRY_KEY_LAST_COVERAGE):
        layer_id, ok = project.readEntry(PROJECT_SCOPE, key, "")
        layer_ids[key] = layer_id if ok else ""
    return {
        "dem_layer": project.mapLayer(layer_ids[ENTRY_KEY_LAST_DEM]),
        "coverage_layer": project.mapLayer(layer_ids[ENTRY_KEY_LAST_COVERAGE]),
    }


def _set_layer_visible(project, layer):
    """Ensure a layer is visible in the project layer tree when present."""
    if layer is None:
        return
    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None:
        node.setItemVisibilityChecked(True)


def _next_3d_view_name(iface: object) -> str:
    """Generate a unique 3D view name for the current QGIS session."""
    existing: list[str] = []
    if hasattr(iface, "mapCanvases3D"):
        existing = iface.mapCanvases3D() or []
    return "{} {}".format(VIEW_NAME_PREFIX, len(existing) + 1)


def open_nowires_3d_view(iface, scene_mode=SCENE_MODE_LOCAL, project=None):
    """Create a new QGIS 3D map canvas using the latest NoWires layers."""
    is_windows = sys.platform == "win32"
    if is_windows:
        dialog = Windows3DFallbackDialog(parent=iface.mainWindow())
        dialog.exec()
        if dialog.clickedButton() == dialog.highlight_button:
            if dialog.highlight_checkbox and dialog.highlight_checkbox.isChecked():
                highlight_nowires_layers(iface, project=project)
        return None

    if project is None:
        project = QgsProject.instance()
    layers = resolve_nowires_3d_layers(project)
    dem_layer = layers["dem_layer"]
    coverage_layer = layers["coverage_layer"]

    if dem_layer is None:
        iface.messageBar().pushWarning(
            "NoWires",
            "No DEM layer found for 3D. Run Coverage Analysis first.",
        )
        return None

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
