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

from .coverage_legend import remove_coverage_legend
from .coverage_opacity import find_latest_coverage_layer, CoverageOpacityDialog
from .provider import NoWiresProvider
from .three_d import SCENE_MODE_GLOBE, SCENE_MODE_LOCAL, open_nowires_3d_view
from .cache_manager import clear_dem_cache, format_cache_size, get_cache_size

cmd_folder = os.path.dirname(__file__)

_MENU_NAME = "NoWires" if sys.platform == "darwin" else "&NoWires"


def _stale_temp_dir_count(max_entries: int = 1000) -> int:
    temp_base = tempfile.gettempdir()
    prefixes = ("nowires_",)
    entries: list[str] = []
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
        self._pattern_preview_dialog = None

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
        # (label, slot, on_toolbar)
        action_specs = [
            ("Point-to-Point Analysis", self.run_p2p, True),
            ("Coverage Analysis", self.run_coverage, False),
            ("Contour Lines", self.run_contour, False),
            ("Coverage Opacity", self.run_coverage_opacity, False),
            ("Open 3D View", self.run_open_3d_view, False),
            ("Coverage Comparison", self.run_comparison, True),
            ("Batch P2P Analysis", self.run_batch, True),
            ("Preview Antenna Pattern", self.run_pattern_preview, False),
            ("Clear DEM Cache", self.run_clear_cache, False),
        ]
        for label, slot, on_toolbar in action_specs:
            act = QAction(QIcon(icon), label, self.iface.mainWindow())
            act.triggered.connect(slot)
            self.iface.addPluginToMenu(_MENU_NAME, act)
            self._menu_actions.append(act)
            if on_toolbar:
                self._toolbar_actions.append(act)
                self.iface.addToolBarIcon(act)

        QTimer.singleShot(5000, self._warn_stale_temp_dirs)
        QTimer.singleShot(5000, self._cleanup_stale_shared_memory)

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

    @staticmethod
    def _cleanup_stale_shared_memory():
        try:
            from .shared_dem_grid import cleanup_stale_shm_entries
            cleanup_stale_shm_entries("/dev/shm", os.geteuid())
        except Exception:
            pass

    def run_clear_cache(self):
        """Show current cache size and clear DEM/WorldCover tiles on confirmation."""
        try:
            count, size_bytes = get_cache_size()
            if count == 0:
                self.iface.messageBar().pushInfo("NoWires", "Cache is empty.")
                return
            from qgis.PyQt.QtWidgets import QMessageBox
            sb = QMessageBox.StandardButton
            msg = format_cache_size(count, size_bytes) + "\n\nDelete all cached tiles?"
            if QMessageBox.question(
                self.iface.mainWindow(), "NoWires — Clear cache",
                msg, sb.Yes | sb.No, sb.No) != sb.Yes:
                return
            removed, freed = clear_dem_cache()
            self.iface.messageBar().pushSuccess(
                "NoWires", "Removed {} cached tile(s) (~{:.1f} MB freed).".format(
                    removed, freed / 1048576.0))
        except Exception as exc:
            self.iface.messageBar().pushWarning(
                "NoWires", "Cache cleanup failed: {}".format(exc))

    def unload(self):
        """Remove plugin elements."""
        if self._opacity_dialog is not None:
            self._opacity_dialog.close()
            self._opacity_dialog = None
        if self._pattern_preview_dialog is not None:
            self._pattern_preview_dialog.close()
            self._pattern_preview_dialog = None
        remove_coverage_legend()
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        for action in getattr(self, "_menu_actions", []):
            self.iface.removePluginMenu(_MENU_NAME, action)
        for action in getattr(self, "_toolbar_actions", []):
            self.iface.removeToolBarIcon(action)

    def run_p2p(self):
        import processing
        processing.execAlgorithmDialog("nowires:p2p_analysis")

    def run_coverage(self):
        import processing
        processing.execAlgorithmDialog("nowires:coverage_analysis")

    def run_contour(self):
        import processing
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
        parent = self.iface.mainWindow()
        self._opacity_dialog = CoverageOpacityDialog(
            layer, parent=parent
        )
        self._opacity_dialog.show()

    def run_open_3d_view(self):
        parent = self.iface.mainWindow()
        mode_label, ok = QInputDialog.getItem(
            parent,
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
        import processing
        processing.execAlgorithmDialog("nowires:coverage_comparison")

    def run_batch(self):
        import processing
        processing.execAlgorithmDialog("nowires:batch_p2p_analysis")

    def run_pattern_preview(self):
        from .antenna_pattern_preview import AntennaPatternPreviewDialog
        if self._pattern_preview_dialog is not None:
            self._pattern_preview_dialog.close()
        dlg = AntennaPatternPreviewDialog(parent=self.iface.mainWindow())
        dlg.show()
        self._pattern_preview_dialog = dlg
