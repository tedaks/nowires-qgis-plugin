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


Profile chart display for P2P analysis using matplotlib.
"""

import contextlib
import logging

import numpy as np

from NoWires.constants import FRESNEL_60PCT_FACTOR
from NoWires.p2p.chart_helpers import (
    add_obstruction_annotations,
    setup_tooltip,
    make_save_png,
    make_export_csv,
)

logger = logging.getLogger(__name__)

try:
    from qgis.PyQt.QtCore import QT_VERSION_STR
    _QT_VER = tuple(int(x) for x in QT_VERSION_STR.split("."))[:2]
    if _QT_VER < (6, 0):
        logger.warning("p2p_chart.py requires Qt 6+; got %s", QT_VERSION_STR)
except ImportError:
    pass

__all__ = ["show_profile_chart"]


def show_profile_chart(
    distances, elevations, terrain_bulge, los_h, fresnel_r, dist_m,
    tx_h, rx_h, f_mhz, result, k_factor, tx_power, tx_gain, rx_gain,
    cable_loss, rx_sens, prx_dbm=None, margin_db=None, itm_loss_db=None,
):
    try:
        import matplotlib
        matplotlib.use("QtAgg")
        from matplotlib.figure import Figure
        from qgis.PyQt.QtWidgets import (QDockWidget, QWidget, QVBoxLayout,
                                          QToolBar, QCheckBox, QPushButton)
        from qgis.PyQt.QtCore import Qt
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    except ImportError:
        logger.warning("matplotlib not available, skipping profile chart")
        return

    import qgis.utils
    if qgis.utils.iface is None:
        logger.debug("P2P chart skipped: QGIS iface not available (headless mode)")
        return

    d_km = np.asarray(distances, dtype=np.float64) / 1000.0

    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    terrain_fill = ax.fill_between(
        d_km, np.min(terrain_bulge) - 10, terrain_bulge,
        color="#8B6914", alpha=0.5, label="Terrain",
    )
    los_line, = ax.plot(d_km, los_h, "g--", linewidth=1.2, label="Line of Sight")
    f1_upper, = ax.plot(d_km, los_h + fresnel_r, "c:", linewidth=0.8)
    f1_lower, = ax.plot(d_km, los_h - fresnel_r, "c:", linewidth=0.8)
    f1_fill = ax.fill_between(
        d_km, los_h - fresnel_r, los_h + fresnel_r,
        color="cyan", alpha=0.15, label="1st Fresnel Zone",
    )
    f60_upper, = ax.plot(d_km, los_h - FRESNEL_60PCT_FACTOR * fresnel_r, "b-", linewidth=0.5)
    f60_fill = ax.fill_between(
        d_km, los_h - fresnel_r, los_h - FRESNEL_60PCT_FACTOR * fresnel_r,
        color="blue", alpha=0.12, label="Fresnel Violation Band (>40%)",
    )
    if len(los_h) > 0:
        tx_marker, = ax.plot(0, los_h[0], "r^", markersize=12, label="TX", zorder=5)
        rx_marker, = ax.plot(d_km[-1], los_h[-1], "rv", markersize=12, label="RX", zorder=5)
    else:
        tx_marker, rx_marker = None, None
    ax.set_xlim(d_km[0], d_km[-1])
    ax.set_ylim(np.min(terrain_bulge) - 10,
                max(np.max(los_h + fresnel_r), np.max(terrain_bulge) + 10))
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Height (m)")
    ax.set_title("P2P Profile: {:.1f} MHz, {:.2f} km (k={:.3f})".format(
        f_mhz, dist_m / 1000, k_factor))
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    from NoWires.p2p.chart_format import build_chart_status_text
    status_text = build_chart_status_text(result, prx_dbm, margin_db, itm_loss_db=itm_loss_db)
    ax.text(
        0.02, 0.98, status_text,
        transform=ax.transAxes, fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
    )

    obstruction_annotations = add_obstruction_annotations(
        ax, d_km, terrain_bulge, los_h, fresnel_r)
    fig.tight_layout()
    toggle_state = {"terrain": True, "los": True, "fresnel": True,
                    "violation_band": True, "antennas": True, "obstructions": True}
    _destroyed = False

    def _set_obstructions_visible(visible):
        # Qt6 workaround: defer annotation removal so the paint cycle finishes.
        if visible and not obstruction_annotations:
            obstruction_annotations.extend(add_obstruction_annotations(
                ax, d_km, terrain_bulge, los_h, fresnel_r))
            fig.canvas.draw_idle()
        elif not visible and obstruction_annotations:
            pending = list(obstruction_annotations)
            obstruction_annotations.clear()
            from qgis.PyQt.QtCore import QTimer
            def _rm():
                for ann in pending:
                    ann.remove()
                fig.canvas.draw_idle()
            Qt_rm = QTimer
            Qt_rm.singleShot(0, _rm)

    def update_visibility():
        if _destroyed:
            return
        from qgis.PyQt.QtCore import QTimer
        def _a():
            try:
                for art, k in [(terrain_fill,"terrain"),(los_line,"los"),
                    (f1_upper,"fresnel"),(f1_lower,"fresnel"),(f1_fill,"fresnel"),
                    (f60_upper,"violation_band"),(f60_fill,"violation_band"),
                    (tx_marker,"antennas"),(rx_marker,"antennas")]:
                    if art is not None:
                        art.set_visible(toggle_state[k])
                _set_obstructions_visible(toggle_state["obstructions"])
                fig.canvas.draw_idle()
            except Exception:
                logger.exception("P2P chart visibility update failed")
        QTimer.singleShot(0, _a)

    from qgis.utils import iface as qgis_iface
    dock = QDockWidget("P2P Profile Chart", qgis_iface.mainWindow())
    dock.setFloating(True)
    dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dock.setWindowFlag(Qt.WindowType.Tool)
    toolbar = QToolBar("Chart Controls")
    btn_png = QPushButton("Save PNG", toolbar)
    btn_csv = QPushButton("Export CSV", toolbar)
    btn_png.clicked.connect(make_save_png(fig, f_mhz, dist_m, dock))
    btn_csv.clicked.connect(make_export_csv(
        distances, terrain_bulge, los_h, fresnel_r, f_mhz, dist_m, dock))
    def _make_toggle(key):
        def _toggle(state):
            toggle_state[key] = int(state) == int(Qt.CheckState.Checked)
            update_visibility()
        return _toggle

    toolbar.addWidget(btn_png)
    toolbar.addWidget(btn_csv)
    toolbar.addSeparator()
    for label, key in [("Terrain", "terrain"), ("LOS", "los"), ("Fresnel", "fresnel"),
                       ("60% Band", "violation_band"), ("Antennas", "antennas"),
                       ("Obstructions", "obstructions")]:
        cb = QCheckBox(label, toolbar)
        cb.setChecked(True)
        cb.checkStateChanged.connect(_make_toggle(key))
        toolbar.addWidget(cb)

    _tooltip_cid = [None]
    def _on_destroy():
        nonlocal _destroyed
        _destroyed = True
        if _tooltip_cid[0] is not None:
            with contextlib.suppress(Exception):
                fig.canvas.mpl_disconnect(_tooltip_cid[0])
            _tooltip_cid[0] = None
        for cb in toolbar.findChildren(QCheckBox):
            with contextlib.suppress(RuntimeError):
                cb.blockSignals(True)
        import matplotlib.pyplot as plt
        with contextlib.suppress(Exception):
            fig.clear()
        with contextlib.suppress(Exception):
            plt.close(fig)
    canvas = FigureCanvasQTAgg(fig)
    dock.destroyed.connect(_on_destroy)
    tooltip_cid = setup_tooltip(ax, fig, d_km, distances, terrain_bulge, los_h, fresnel_r)
    _tooltip_cid[0] = tooltip_cid
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(toolbar)
    layout.addWidget(canvas)
    dock.setWidget(container)
    qgis_iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.setFloating(True)
