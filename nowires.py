# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 by Bortre Tenamo
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
"""

import os

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.PyQt.QtWidgets import QInputDialog

from qgis.core import QgsApplication
import processing

from .coverage_legend import remove_coverage_legend
from .coverage_opacity import find_latest_coverage_layer, CoverageOpacityDialog
from .provider import NoWiresProvider
from .three_d import SCENE_MODE_GLOBE, SCENE_MODE_LOCAL, open_nowires_3d_view

cmd_folder = os.path.dirname(__file__)


class NoWiresPlugin:
    """Main NoWires plugin class.

    Registers the processing provider and adds toolbar/menu entries.
    All functionality is exposed via QGIS Processing algorithms.
    """

    def __init__(self, iface):
        self.provider = None
        self.iface = iface

    def initProcessing(self):
        """Register the processing provider."""
        self.provider = NoWiresProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Initialize GUI elements."""
        self.initProcessing()

        icon = os.path.join(cmd_folder, "logo.png")

        # P2P Analysis action
        self.p2p_action = QAction(
            QIcon(icon), "Point-to-Point Analysis", self.iface.mainWindow()
        )
        self.p2p_action.triggered.connect(self.run_p2p)
        self.iface.addPluginToMenu("&NoWires", self.p2p_action)
        self.iface.addToolBarIcon(self.p2p_action)

        # Coverage action
        self.coverage_action = QAction(
            QIcon(icon), "Coverage Analysis", self.iface.mainWindow()
        )
        self.coverage_action.triggered.connect(self.run_coverage)
        self.iface.addPluginToMenu("&NoWires", self.coverage_action)

        # Contour Lines action
        self.contour_action = QAction(
            QIcon(icon), "Contour Lines", self.iface.mainWindow()
        )
        self.contour_action.triggered.connect(self.run_contour)
        self.iface.addPluginToMenu("&NoWires", self.contour_action)

        # Coverage Opacity action
        self.opacity_action = QAction(
            QIcon(icon), "Coverage Opacity", self.iface.mainWindow()
        )
        self.opacity_action.triggered.connect(self.run_coverage_opacity)
        self.iface.addPluginToMenu("&NoWires", self.opacity_action)

        # 3D View action
        self.open_3d_action = QAction(
            QIcon(icon), "Open 3D View", self.iface.mainWindow()
        )
        self.open_3d_action.triggered.connect(self.run_open_3d_view)
        self.iface.addPluginToMenu("&NoWires", self.open_3d_action)

        self._opacity_dialog = None

    def unload(self):
        """Remove plugin elements."""
        if self._opacity_dialog is not None:
            self._opacity_dialog.close()
            self._opacity_dialog = None
        remove_coverage_legend()
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removePluginMenu("&NoWires", self.p2p_action)
        self.iface.removePluginMenu("&NoWires", self.coverage_action)
        self.iface.removePluginMenu("&NoWires", self.contour_action)
        self.iface.removePluginMenu("&NoWires", self.opacity_action)
        self.iface.removePluginMenu("&NoWires", self.open_3d_action)
        self.iface.removeToolBarIcon(self.p2p_action)

    def run_p2p(self):
        processing.execAlgorithmDialog("nowires:p2p_analysis")

    def run_coverage(self):
        processing.execAlgorithmDialog("nowires:coverage_analysis")

    def run_contour(self):
        processing.execAlgorithmDialog("nowires:contour_lines")

    def run_coverage_opacity(self):
        layer = find_latest_coverage_layer()
        if layer is None:
            self.iface.messageBar().pushWarning(
                "NoWires",
                "No coverage layer found. Run Coverage Analysis first.",
            )
            return
        if self._opacity_dialog is not None:
            self._opacity_dialog.close()
        self._opacity_dialog = CoverageOpacityDialog(
            layer, parent=self.iface.mainWindow()
        )
        self._opacity_dialog.show()

    def run_open_3d_view(self):
        mode_label, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            "NoWires 3D View",
            "Scene mode",
            ["Local terrain", "Globe"],
            0,
            False,
        )
        if not ok:
            return

        scene_mode = SCENE_MODE_GLOBE if mode_label == "Globe" else SCENE_MODE_LOCAL
        QTimer.singleShot(
            0, lambda mode=scene_mode: open_nowires_3d_view(self.iface, scene_mode=mode)
        )
