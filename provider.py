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
"""


# NoWires Processing Provider.
#
# Registers all processing algorithms: P2P analysis, coverage analysis,
# coverage comparison, and batch P2P analysis.

import importlib
import logging

import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

logger = logging.getLogger(__name__)

_ALGORITHM_CLASSES = [
    ("algorithm.p2p", "P2PAlgorithm"),
    ("algorithm.coverage", "CoverageAlgorithm"),
    ("algorithm.coverage_comparison", "CoverageComparisonAlgorithm"),
    ("algorithm.batch", "BatchAnalysisAlgorithm"),
]


class NoWiresProvider(QgsProcessingProvider):
    """Processing provider for NoWires radio propagation and terrain tools."""

    def __init__(self):
        super().__init__()

    def unload(self):
        super().unload()

    def loadAlgorithms(self):
        for module_name, class_name in _ALGORITHM_CLASSES:
            try:
                mod = importlib.import_module(".{}".format(module_name), __package__)
                cls = getattr(mod, class_name)
                self.addAlgorithm(cls())
            except Exception as exc:
                logger.exception("Failed to load algorithm %s.%s", module_name, class_name)
                from qgis.core import QgsMessageLog
                QgsMessageLog.logMessage(
                    "NoWires: algorithm {}.{} failed to load: {}".format(
                        module_name, class_name, exc),
                    "NoWires")

    def id(self):
        return "nowires"

    def name(self):
        return self.tr("NoWires")

    def icon(self):
        cmd_folder = os.path.dirname(__file__)
        return QIcon(os.path.join(cmd_folder, "logo.png"))

    def longName(self):
        return self.tr("NoWires — Radio Propagation & Terrain Analysis")
