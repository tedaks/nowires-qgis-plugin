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

import logging

import numpy as np

from .defaults import FRESNEL_60PCT_FACTOR

logger = logging.getLogger(__name__)

try:
    from qgis.PyQt.QtCore import QT_VERSION_STR
    _QT_VER = tuple(int(x) for x in QT_VERSION_STR.split("."))[:2]
    if _QT_VER < (6, 0):
        logger.warning("p2p_chart.py requires Qt 6+; got %s", QT_VERSION_STR)
except ImportError:
    pass

__all__ = ["show_profile_chart"]


def _add_obstruction_annotations(ax, d_km, terrain_bulge, los_h, fresnel_r):
    from .p2p_chart_format import build_obstruction_data
    annotations = []
    for idx, ob_x, ob_y, _los, _fr, deficit in build_obstruction_data(
        d_km, terrain_bulge, los_h, fresnel_r
    ):
        ann = ax.annotate(
            "OBSTRUCTION\nDist: {:.1f} km\nHeight: {:.1f} m\nDeficit: {:.1f} m".format(
                ob_x, ob_y, deficit
            ),
            xy=(ob_x, ob_y), xytext=(0, 20),
            arrowprops=dict(arrowstyle="->", color="red", lw=1.2),
            textcoords="offset points", fontsize=7, color="red",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
            ha="center",
        )
        annotations.append(ann)
    return annotations


def _setup_tooltip(ax, fig, d_km, distances, terrain_bulge, los_h, fresnel_r):
    tooltip = ax.text(
        0, 0, "", fontsize=8, visible=False,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8),
    )
    vline = ax.axvline(x=0, color="gray", linewidth=0.8, visible=False)

    def on_motion(event):
        if event.inaxes != ax or event.xdata is None:
            tooltip.set_visible(False)
            vline.set_visible(False)
            fig.canvas.draw_idle()
            return
        if len(d_km) == 0:
            return
        idx = np.argmin(np.abs(d_km - event.xdata))
        if idx >= len(distances):
            return
        dist_val = distances[idx]
        elev_val = terrain_bulge[idx]
        los_val = los_h[idx]
        fresnel_val = fresnel_r[idx]
        clear_val = los_val - fresnel_val - elev_val
        tooltip.set_text(
            "Dist: {:.1f} km\nTerrain: {:.1f} m\nLOS: {:.1f} m\n"
            "Fresnel R: {:.1f} m\nClearance: {:.1f} m".format(
                dist_val / 1000, elev_val, los_val, fresnel_val, clear_val
            )
        )
        tooltip.set_visible(True)
        vline.set_visible(True)
        vline.set_xdata([event.xdata, event.xdata])
        tooltip_x = event.xdata
        mid = (d_km[-1] + d_km[0]) / 2
        span = d_km[-1] - d_km[0]
        tooltip_x = event.xdata - span * 0.15 if tooltip_x > mid else event.xdata + span * 0.02
        tooltip.set_position((tooltip_x, max(elev_val, los_val) + 3))
        fig.canvas.draw_idle()

    cid = fig.canvas.mpl_connect("motion_notify_event", on_motion)
    return cid


def _make_save_png(fig, f_mhz, dist_m, dock):
    from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
    def save_png():
        try:
            default_name = "p2p_profile_{:.0f}MHz_{:.1f}km.png".format(f_mhz, dist_m / 1000)
            path, _ = QFileDialog.getSaveFileName(dock, "Save PNG", default_name, "PNG Files (*.png)")
            if path:
                if not path.lower().endswith(".png"):
                    path += ".png"
                fig.savefig(path, dpi=300, bbox_inches="tight")
                QMessageBox.information(dock, "Saved", "Chart saved to:\n" + path)
        except Exception as e:
            logger.warning("Failed to save PNG: %s", e)
            QMessageBox.warning(dock, "Error", "Failed to save PNG: " + str(e))
    return save_png


def _make_export_csv(distances, terrain_bulge, los_h, fresnel_r, f_mhz, dist_m, dock):
    from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
    clearances = los_h - fresnel_r - terrain_bulge
    def export_csv():
        try:
            default_name = "p2p_profile_{:.0f}MHz_{:.1f}km.csv".format(f_mhz, dist_m / 1000)
            path, _ = QFileDialog.getSaveFileName(dock, "Export CSV", default_name, "CSV Files (*.csv)")
            if path:
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                obstructs_los = terrain_bulge > los_h
                with open(path, "w", newline="") as f:
                    f.write("distance_m,terrain_elevation_m,los_m,fresnel_radius_m,clearance_m,obstructs_los\n")
                    for i in range(len(distances)):
                        f.write("{:.2f},{:.2f},{:.2f},{:.2f},{:.2f},{:.0f}\n".format(
                            distances[i], terrain_bulge[i], los_h[i],
                            fresnel_r[i], clearances[i], 1 if obstructs_los[i] else 0,
                        ))
                QMessageBox.information(dock, "Exported", "Data exported to:\n" + path)
        except Exception as e:
            logger.warning("Failed to export CSV: %s", e)
            QMessageBox.warning(dock, "Error", "Failed to export CSV: " + str(e))
    return export_csv


def show_profile_chart(
    distances, elevations, terrain_bulge, los_h, fresnel_r, dist_m,
    tx_h, rx_h, f_mhz, result, k_factor, tx_power, tx_gain, rx_gain,
    cable_loss, rx_sens, prx_dbm=None, margin_db=None,
):
    try:
        import matplotlib
        matplotlib.use("QtAgg")
        from matplotlib.figure import Figure
        from qgis.PyQt.QtWidgets import (
            QDockWidget, QWidget, QVBoxLayout, QToolBar, QCheckBox, QPushButton,
        )
        from qgis.PyQt.QtCore import Qt
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    except ImportError:
        logger.warning("matplotlib not available, skipping profile chart")
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
    ax.set_xlim(d_km[0], d_km[-1])
    ax.set_ylim(np.min(terrain_bulge) - 10, max(np.max(los_h + fresnel_r), np.max(terrain_bulge) + 10))
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Height (m)")
    ax.set_title("P2P Profile: {:.1f} MHz, {:.2f} km (k={:.3f})".format(
        f_mhz, dist_m / 1000, k_factor))
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    from .p2p_chart_format import build_chart_status_text
    status_text = build_chart_status_text(result, prx_dbm, margin_db)
    ax.text(
        0.02, 0.98, status_text,
        transform=ax.transAxes, fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
    )

    obstruction_annotations = _add_obstruction_annotations(ax, d_km, terrain_bulge, los_h, fresnel_r)
    fig.tight_layout()
    toggle_state = {
        "terrain": True, "los": True, "fresnel": True,
        "violation_band": True, "antennas": True, "obstructions": True,
    }

    def _set_obstructions_visible(visible):
        # Remove/recreate instead of set_visible: toggling visibility on an
        # Annotation with arrowprops crashes the QtAgg backend on QGIS 4 (Qt6)
        # when the FancyArrowPatch is hidden mid-redraw.
        if visible and not obstruction_annotations:
            obstruction_annotations.extend(_add_obstruction_annotations(
                ax, d_km, terrain_bulge, los_h, fresnel_r))
        elif not visible:
            while obstruction_annotations:
                try:
                    obstruction_annotations.pop().remove()
                except (ValueError, NotImplementedError):
                    pass

    def update_visibility():
        try:
            terrain_fill.set_visible(toggle_state["terrain"])
            los_line.set_visible(toggle_state["los"])
            f1_upper.set_visible(toggle_state["fresnel"])
            f1_lower.set_visible(toggle_state["fresnel"])
            f1_fill.set_visible(toggle_state["fresnel"])
            f60_upper.set_visible(toggle_state["violation_band"])
            f60_fill.set_visible(toggle_state["violation_band"])
            tx_marker.set_visible(toggle_state["antennas"])
            rx_marker.set_visible(toggle_state["antennas"])
            _set_obstructions_visible(toggle_state["obstructions"])
            fig.canvas.draw_idle()
        except Exception:
            # PyQt6 may abort the process on an unraisable exception in a slot.
            logger.exception("P2P chart visibility update failed")

    from qgis.utils import iface as qgis_iface
    dock = QDockWidget("P2P Profile Chart", qgis_iface.mainWindow())
    dock.setFloating(True)
    dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dock.setWindowFlag(Qt.WindowType.Tool)
    toolbar = QToolBar("Chart Controls")
    btn_png = QPushButton("Save PNG", toolbar)
    btn_csv = QPushButton("Export CSV", toolbar)
    btn_png.clicked.connect(_make_save_png(fig, f_mhz, dist_m, dock))
    btn_csv.clicked.connect(_make_export_csv(distances, terrain_bulge, los_h, fresnel_r, f_mhz, dist_m, dock))
    def _make_toggle(key):
        def _toggle(state):
            toggle_state[key] = int(state) == int(Qt.CheckState.Checked)
            update_visibility()
        return _toggle

    toolbar.addWidget(btn_png)
    toolbar.addWidget(btn_csv)
    toolbar.addSeparator()
    for label, key in [
        ("Terrain", "terrain"), ("LOS", "los"), ("Fresnel", "fresnel"),
        ("60% Band", "violation_band"), ("Antennas", "antennas"), ("Obstructions", "obstructions"),
    ]:
        cb = QCheckBox(label, toolbar)
        cb.setChecked(True)
        cb.checkStateChanged.connect(_make_toggle(key))
        toolbar.addWidget(cb)

    _tooltip_cid = [None]
    def _on_close_event(event):
        if _tooltip_cid[0] is not None:
            try:
                fig.canvas.mpl_disconnect(_tooltip_cid[0])
            except Exception:
                pass
            _tooltip_cid[0] = None

    class _ChartCanvas(FigureCanvasQTAgg):
        def closeEvent(self, event):
            _on_close_event(event)
            super().closeEvent(event)

    canvas = _ChartCanvas(fig)
    tooltip_cid = _setup_tooltip(ax, fig, d_km, distances, terrain_bulge, los_h, fresnel_r)
    _tooltip_cid[0] = tooltip_cid
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(toolbar)
    layout.addWidget(canvas)
    dock.setWidget(container)
    qgis_iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)