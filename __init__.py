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
"""


class _NoOpPlugin:
    """Placeholder plugin returned in multiprocessing subprocesses.

    On macOS (spawn start method), child processes re-import the plugin and
    would otherwise call ``initGui``, opening duplicate QGIS windows.
    Returning this no-op class prevents that.
    """

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        pass

    def unload(self):
        pass


def classFactory(iface):
    """Load NoWires plugin class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    import multiprocessing

    if multiprocessing.current_process().name != "MainProcess":
        return _NoOpPlugin(iface)
    from .nowires import NoWiresPlugin
    return NoWiresPlugin(iface)
