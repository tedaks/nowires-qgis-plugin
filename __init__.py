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


class _NoOpPlugin:
    """Placeholder plugin returned in multiprocessing subprocesses.

    On macOS (spawn start method), child processes re-import the plugin and
    would otherwise call ``initGui``, opening duplicate QGIS windows.
    Returning this no-op class prevents that.
    """

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self._menu_actions = []
        self._toolbar_actions = []
        self._opacity_dialog = None

    def initGui(self):
        pass

    def unload(self):
        pass

    def __getattr__(self, name):
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'. "
            f"This is a NoOp plugin for subprocess isolation. "
            f"The requested attribute '{name}' is not available."
        )


def classFactory(iface):
    """Load NoWires plugin class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    import multiprocessing
    import sys

    if sys.platform == "win32":
        multiprocessing.freeze_support()

    if multiprocessing.current_process().name != "MainProcess":
        return _NoOpPlugin(iface)

    _ensure_gdal_env()
    from osgeo import gdal
    gdal.UseExceptions()
    from NoWires.nowires import NoWiresPlugin
    return NoWiresPlugin(iface)


def _ensure_gdal_env():
    """Ensure GDAL_DATA and PROJ_LIB point to the QGIS-bundled directories.

    On macOS, QGIS.app bundles GDAL and PROJ data in non-standard locations.
    If another plugin or user shell profile overrides these env vars, GDAL
    operations (especially osr.SpatialReference) may fail silently or raise.
    """
    import os
    import sys

    if sys.platform != "darwin":
        return

    try:
        from qgis.core import QgsApplication
    except ImportError:
        return

    app = QgsApplication.instance()
    if app is None:
        return

    prefix = None
    for attr in ("prefixPath", "pkgDataPath", "srsDatabaseFilePath"):
        candidate = getattr(app, attr, None)
        if callable(candidate):
            candidate = candidate()
        if candidate:
            prefix = str(candidate)
            break

    if prefix is None:
        return

    gdal_data = os.path.join(prefix, "gdal")
    proj_lib = os.path.join(prefix, "proj")
    for candidate in [prefix, os.path.dirname(prefix)]:
        gd = os.path.join(candidate, "gdal")
        pl = os.path.join(candidate, "proj")
        if os.path.isdir(gd):
            gdal_data = gd
        if os.path.isdir(pl):
            proj_lib = pl

    if os.path.isdir(gdal_data):
        os.environ.setdefault("GDAL_DATA", gdal_data)
    if os.path.isdir(proj_lib):
        os.environ.setdefault("PROJ_LIB", proj_lib)
