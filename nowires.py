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
"""

import os
import sys
import tempfile

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QAction, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QInputDialog

from qgis.core import QgsApplication
import processing

from .coverage_legend import remove_coverage_legend
from .coverage_opacity import find_latest_coverage_layer, CoverageOpacityDialog
from .provider import NoWiresProvider
from .three_d import SCENE_MODE_GLOBE, SCENE_MODE_LOCAL, open_nowires_3d_view
from .cache_manager import clear_dem_cache

cmd_folder = os.path.dirname(__file__)

_MENU_NAME = "NoWires" if sys.platform == "darwin" else "&NoWires"


def _stale_temp_dir_count(max_entries=1000):
    temp_base = tempfile.gettempdir()
    prefixes = ("nowires_",)
    entries = []
    for base in (temp_base,):
        try:
            entries.extend(
                e for e in os.listdir(base)
                if any(e.startswith(p) for p in prefixes)
            )
            if len(entries) >= max_entries:
                return len(entries)
        except OSError:
            pass
    try:
        from .dem_downloader import get_temp_dir
        user_dir = get_temp_dir()
        for e in os.listdir(user_dir):
            if any(e.startswith(p) for p in prefixes) and e not in entries:
                entries.append(e)
        if len(entries) >= max_entries:
            return len(entries)
    except Exception:
        pass
    return len(entries)


class NoWiresPlugin:
    """Main NoWires plugin class.

    Registers the processing provider and adds toolbar/menu entries.
    All functionality is exposed via QGIS Processing algorithms.
    """

    def __init__(self, iface):
        self.provider = None
        self.iface = iface
        self._toolbar_actions = []
        self._menu_actions = []
        self._opacity_dialog = None

    def initProcessing(self):
        """Register the processing provider."""
        registry = QgsApplication.processingRegistry()
        if self.provider is not None:
            try:
                registry.removeProvider(self.provider)
            except Exception:
                pass
        self.provider = NoWiresProvider()
        registry.addProvider(self.provider)

    def initGui(self):
        """Initialize GUI elements."""
        self.initProcessing()

        icon_path = os.path.join(cmd_folder, "logo.png")
        retina_path = os.path.join(cmd_folder, "logo@2x.png")
        if sys.platform == "darwin" and os.path.exists(retina_path):
            icon = QIcon(QPixmap(retina_path))
            icon.addFile(icon_path)
        else:
            icon = QIcon(QPixmap(icon_path)) if os.path.exists(icon_path) else QIcon(icon_path)
        self._toolbar_actions = []
        self._menu_actions = []

        # P2P Analysis action
        self.p2p_action = QAction(
            QIcon(icon), "Point-to-Point Analysis", self.iface.mainWindow()
        )
        self.p2p_action.triggered.connect(self.run_p2p)
        self.iface.addPluginToMenu(_MENU_NAME, self.p2p_action)
        self._toolbar_actions.append(self.p2p_action)
        self._menu_actions.append(self.p2p_action)

        # Coverage action
        self.coverage_action = QAction(
            QIcon(icon), "Coverage Analysis", self.iface.mainWindow()
        )
        self.coverage_action.triggered.connect(self.run_coverage)
        self.iface.addPluginToMenu(_MENU_NAME, self.coverage_action)
        self._menu_actions.append(self.coverage_action)

        # Contour Lines action
        self.contour_action = QAction(
            QIcon(icon), "Contour Lines", self.iface.mainWindow()
        )
        self.contour_action.triggered.connect(self.run_contour)
        self.iface.addPluginToMenu(_MENU_NAME, self.contour_action)
        self._menu_actions.append(self.contour_action)

        # Coverage Opacity action
        self.opacity_action = QAction(
            QIcon(icon), "Coverage Opacity", self.iface.mainWindow()
        )
        self.opacity_action.triggered.connect(self.run_coverage_opacity)
        self.iface.addPluginToMenu(_MENU_NAME, self.opacity_action)
        self._menu_actions.append(self.opacity_action)

        # 3D View action
        self.open_3d_action = QAction(
            QIcon(icon), "Open 3D View", self.iface.mainWindow()
        )
        self.open_3d_action.triggered.connect(self.run_open_3d_view)
        self.iface.addPluginToMenu(_MENU_NAME, self.open_3d_action)
        self._menu_actions.append(self.open_3d_action)

        # Coverage Comparison action
        self.comparison_action = QAction(
            QIcon(icon), "Coverage Comparison", self.iface.mainWindow()
        )
        self.comparison_action.triggered.connect(self.run_comparison)
        self.iface.addPluginToMenu(_MENU_NAME, self.comparison_action)
        self._toolbar_actions.append(self.comparison_action)
        self._menu_actions.append(self.comparison_action)

        # Batch P2P Analysis action
        self.batch_action = QAction(
            QIcon(icon), "Batch P2P Analysis", self.iface.mainWindow()
        )
        self.batch_action.triggered.connect(self.run_batch)
        self.iface.addPluginToMenu(_MENU_NAME, self.batch_action)
        self._toolbar_actions.append(self.batch_action)
        self._menu_actions.append(self.batch_action)

        # Clear DEM Cache action
        self.clear_cache_action = QAction(
            QIcon(icon), "Clear DEM Cache", self.iface.mainWindow()
        )
        self.clear_cache_action.triggered.connect(self.run_clear_cache)
        self.iface.addPluginToMenu(_MENU_NAME, self.clear_cache_action)
        self._menu_actions.append(self.clear_cache_action)

        for action in self._toolbar_actions:
            self.iface.addToolBarIcon(action)

        QTimer.singleShot(5000, self._warn_stale_temp_dirs)

    def _warn_stale_temp_dirs(self):
        """Log a warning about stale temporary directories (deferred from initGui)."""
        stale = _stale_temp_dir_count()
        if stale > 0:
            from qgis.core import QgsMessageLog
            QgsMessageLog.logMessage(
                "NoWires: {} stale temporary director(y/ies) in {}. "
                "These are left for QGIS layer loading and can be "
                "safely deleted when QGIS is closed.".format(stale, tempfile.gettempdir()),
                "NoWires")

    def run_clear_cache(self):
        """Clear cached DEM and WorldCover tiles from the temp directory."""
        try:
            removed, freed_bytes = clear_dem_cache()
            mb = freed_bytes / 1048576.0
            if removed == 0:
                self.iface.messageBar().pushInfo(
                    "NoWires", "No cached tile files found."
                )
            else:
                self.iface.messageBar().pushSuccess(
                    "NoWires",
                    "Removed {} cached tile(s) (~{:.1f} MB freed).".format(
                        removed, mb)
                )
        except Exception as exc:
            self.iface.messageBar().pushWarning(
                "NoWires", "Cache cleanup failed: {}".format(exc)
            )

    def unload(self):
        """Remove plugin elements."""
        if self._opacity_dialog is not None:
            self._opacity_dialog.close()
            self._opacity_dialog = None
        remove_coverage_legend()
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        for action in getattr(self, "_menu_actions", []):
            self.iface.removePluginMenu(_MENU_NAME, action)
        for action in getattr(self, "_toolbar_actions", []):
            self.iface.removeToolBarIcon(action)

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

    def run_comparison(self):
        processing.execAlgorithmDialog("nowires:coverage_comparison")

    def run_batch(self):
        processing.execAlgorithmDialog("nowires:batch_p2p_analysis")
