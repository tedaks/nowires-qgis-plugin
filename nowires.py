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
import sys

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsApplication
import processing

from .coverage_legend import remove_coverage_legend
from .provider import NoWiresProvider

cmd_folder = os.path.dirname(__file__)

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)


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

    def unload(self):
        """Remove plugin elements."""
        remove_coverage_legend()
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removePluginMenu("&NoWires", self.p2p_action)
        self.iface.removePluginMenu("&NoWires", self.coverage_action)
        self.iface.removePluginMenu("&NoWires", self.contour_action)
        self.iface.removeToolBarIcon(self.p2p_action)

    def run_p2p(self):
        processing.execAlgorithmDialog("nowires:p2p_analysis")

    def run_coverage(self):
        processing.execAlgorithmDialog("nowires:coverage_analysis")

    def run_contour(self):
        processing.execAlgorithmDialog("nowires:contour_lines")
