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


NoWires Processing Provider.

Registers all processing algorithms: P2P analysis, coverage analysis,
and contour lines generation.
"""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider


class NoWiresProvider(QgsProcessingProvider):
    """Processing provider for NoWires radio propagation and terrain tools."""

    def __init__(self):
        super().__init__()

    def unload(self):
        pass

    def loadAlgorithms(self):
        from .algorithm_p2p import P2PAlgorithm
        from .algorithm_coverage import CoverageAlgorithm
        from .algorithm_contour import ContourLinesAlgorithm

        self.addAlgorithm(P2PAlgorithm())
        self.addAlgorithm(CoverageAlgorithm())
        self.addAlgorithm(ContourLinesAlgorithm())

    def id(self):
        return "nowires"

    def name(self):
        return self.tr("NoWires")

    def icon(self):
        cmd_folder = os.path.dirname(__file__)
        return QIcon(os.path.join(cmd_folder, "logo.png"))

    def longName(self):
        return self.tr("NoWires — Radio Propagation & Terrain Analysis")
