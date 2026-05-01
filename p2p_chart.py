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


Profile chart display for P2P analysis using matplotlib.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["show_profile_chart"]


def show_profile_chart(
    distances, elevations, terrain_bulge, los_h, fresnel_r, dist_m,
    tx_h, rx_h, f_mhz, result, k_factor, tx_power, tx_gain, rx_gain,
    cable_loss, rx_sens, prx_dbm=None, margin_db=None,
):
    try:
        import matplotlib
        matplotlib.use("QtAgg")
        import matplotlib.pyplot as plt
        from qgis.PyQt.QtWidgets import (
            QDockWidget,
            QWidget,
            QVBoxLayout,
            QToolBar,
            QCheckBox,
            QPushButton,
            QFileDialog,
            QMessageBox,
        )
        from qgis.PyQt.QtCore import Qt
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    except ImportError:
        logger.warning("matplotlib not available, skipping profile chart")
        return

    d_km = np.asarray(distances, dtype=np.float64) / 1000.0

    fig, ax = plt.subplots(figsize=(10, 5))

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

    f60_upper, = ax.plot(d_km, los_h - 0.6 * fresnel_r, "b-", linewidth=0.5)
    f60_fill = ax.fill_between(
        d_km, los_h - fresnel_r, los_h - 0.6 * fresnel_r,
        color="blue", alpha=0.12, label="Fresnel Violation Band (>40%)",
    )

    tx_marker, = ax.plot(0, los_h[0], "r^", markersize=12, label="TX", zorder=5)
    rx_marker, = ax.plot(d_km[-1], los_h[-1], "rv", markersize=12, label="RX", zorder=5)

    ax.set_xlim(d_km[0], d_km[-1])
    ax.set_ylim(np.min(terrain_bulge) - 10, max(np.max(los_h + fresnel_r), np.max(terrain_bulge) + 10))

    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Height (m)")
    ax.set_title(
        "P2P Profile: {:.1f} MHz, {:.2f} km (k={:.3f})".format(
            f_mhz, dist_m / 1000, k_factor
        )
    )
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    prx = prx_dbm
    margin = margin_db
    status = "VIABLE" if margin >= 0 else "NOT VIABLE"
    textstr = (
        "Loss: {:.1f} dB\n"
        "Prx: {:.1f} dBm\n"
        "Margin: {:.1f} dB\n"
        "Status: {}".format(result.loss_db, prx, margin, status)
    )
    props = dict(boxstyle="round", facecolor="wheat", alpha=0.8)
    ax.text(
        0.02, 0.98, textstr,
        transform=ax.transAxes, fontsize=9,
        verticalalignment="top", bbox=props,
    )

    clearances = los_h - fresnel_r - terrain_bulge
    obstruction_indices = np.where(terrain_bulge > los_h - fresnel_r)[0]

    def _local_maxima(indices, arr):
        index_set = set(indices)
        peaks = []
        for idx in indices:
            is_peak = True
            for offset in [-1, 1]:
                neighbor = idx + offset
                if 0 <= neighbor < len(arr) and neighbor in index_set:
                    if arr[neighbor] > arr[idx]:
                        is_peak = False
                        break
                    elif arr[neighbor] == arr[idx] and neighbor < idx:
                        is_peak = False
                        break
            if is_peak:
                peaks.append(idx)
        peaks.sort(key=lambda i: arr[i], reverse=True)
        return peaks[:5]

    obstruction_peaks = _local_maxima(list(obstruction_indices), terrain_bulge)
    obstruction_annotations = []
    for idx in obstruction_peaks:
        ob_x = d_km[idx]
        ob_y = terrain_bulge[idx]
        deficit = ob_y - (los_h[idx] - fresnel_r[idx])
        ann = ax.annotate(
            "OBSTRUCTION\n"
            "Dist: {:.1f} km\n"
            "Height: {:.1f} m\n"
            "Deficit: {:.1f} m".format(ob_x, ob_y, max(0, deficit)),
            xy=(ob_x, ob_y),
            xytext=(0, 20),
            arrowprops=dict(arrowstyle="->", color="red", lw=1.2),
            textcoords="offset points",
            fontsize=7,
            color="red",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
            ha="center",
        )
        obstruction_annotations.append(ann)

    fig.tight_layout()

    canvas = FigureCanvasQTAgg(fig)

    toggle_state = {"terrain": True, "los": True,
                    "fresnel": True, "violation_band": True, "antennas": True,
                    "obstructions": True}

    def update_visibility():
        terrain_fill.set_visible(toggle_state["terrain"])
        los_line.set_visible(toggle_state["los"])
        f1_upper.set_visible(toggle_state["fresnel"])
        f1_lower.set_visible(toggle_state["fresnel"])
        f1_fill.set_visible(toggle_state["fresnel"])
        f60_upper.set_visible(toggle_state["violation_band"])
        f60_fill.set_visible(toggle_state["violation_band"])
        tx_marker.set_visible(toggle_state["antennas"])
        rx_marker.set_visible(toggle_state["antennas"])
        for ann in obstruction_annotations:
            ann.set_visible(toggle_state["obstructions"])
        fig.canvas.draw_idle()


    def save_png():
        try:
            default_name = "p2p_profile_{:.0f}MHz_{:.1f}km.png".format(f_mhz, dist_m / 1000)
            path, _ = QFileDialog.getSaveFileName(
                dock, "Save PNG", default_name, "PNG Files (*.png)"
            )
            if path:
                if not path.lower().endswith(".png"):
                    path += ".png"
                fig.savefig(path, dpi=300, bbox_inches="tight")
                QMessageBox.information(dock, "Saved", "Chart saved to:\n" + path)
        except Exception as e:
            logger.warning("Failed to save PNG: %s", e)
            QMessageBox.warning(dock, "Error", "Failed to save PNG: " + str(e))

    def export_csv():
        try:
            default_name = "p2p_profile_{:.0f}MHz_{:.1f}km.csv".format(f_mhz, dist_m / 1000)
            path, _ = QFileDialog.getSaveFileName(
                dock, "Export CSV", default_name, "CSV Files (*.csv)"
            )
            if path:
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                obstructs_los = terrain_bulge > los_h
                with open(path, "w") as f:
                    f.write("distance_m,terrain_elevation_m,los_m,fresnel_radius_m,clearance_m,obstructs_los\n")
                    for i in range(len(distances)):
                        f.write(
                            "{:.2f},{:.2f},{:.2f},{:.2f},{:.2f},{:.0f}\n".format(
                                distances[i],
                                terrain_bulge[i],
                                los_h[i],
                                fresnel_r[i],
                                clearances[i],
                                1 if obstructs_los[i] else 0,
                            )
                        )
                QMessageBox.information(dock, "Exported", "Data exported to:\n" + path)
        except Exception as e:
            logger.warning("Failed to export CSV: %s", e)
            QMessageBox.warning(dock, "Error", "Failed to export CSV: " + str(e))

    from qgis.utils import iface as qgis_iface
    dock = QDockWidget("P2P Profile Chart", qgis_iface.mainWindow())
    dock.setWidget(QWidget())
    dock.setFloating(True)
    dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def _on_dock_destroyed():
        import matplotlib.pyplot as plt
        plt.close(fig)
    dock.destroyed.connect(_on_dock_destroyed)

    toolbar = QToolBar("Chart Controls")
    btn_png = QPushButton("Save PNG", toolbar)
    btn_csv = QPushButton("Export CSV", toolbar)
    btn_png.clicked.connect(save_png)
    btn_csv.clicked.connect(export_csv)

    cb_terrain = QCheckBox("Terrain", toolbar)
    cb_terrain.setChecked(True)
    cb_los = QCheckBox("LOS", toolbar)
    cb_los.setChecked(True)
    cb_fresnel = QCheckBox("Fresnel", toolbar)
    cb_fresnel.setChecked(True)
    cb_violation = QCheckBox("60% Band", toolbar)
    cb_violation.setChecked(True)
    cb_antennas = QCheckBox("Antennas", toolbar)
    cb_antennas.setChecked(True)
    cb_obstructions = QCheckBox("Obstructions", toolbar)
    cb_obstructions.setChecked(True)

    def _make_toggle(key):
        def _toggle(state):
            toggle_state[key] = int(state) == int(Qt.CheckState.Checked)
            update_visibility()
        return _toggle

    cb_terrain.checkStateChanged.connect(_make_toggle("terrain"))
    cb_los.checkStateChanged.connect(_make_toggle("los"))
    cb_fresnel.checkStateChanged.connect(_make_toggle("fresnel"))
    cb_violation.checkStateChanged.connect(_make_toggle("violation_band"))
    cb_antennas.checkStateChanged.connect(_make_toggle("antennas"))
    cb_obstructions.checkStateChanged.connect(_make_toggle("obstructions"))

    toolbar.addWidget(btn_png)
    toolbar.addWidget(btn_csv)
    toolbar.addSeparator()
    toolbar.addWidget(cb_terrain)
    toolbar.addWidget(cb_los)
    toolbar.addWidget(cb_fresnel)
    toolbar.addWidget(cb_violation)
    toolbar.addWidget(cb_antennas)
    toolbar.addWidget(cb_obstructions)

    tooltip = ax.text(0, 0, "", fontsize=8, visible=False,
                      bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
    vline = ax.axvline(x=0, color="gray", linewidth=0.8, visible=False)

    def on_motion(event):
        if event.inaxes != ax:
            tooltip.set_visible(False)
            vline.set_visible(False)
            fig.canvas.draw_idle()
            return
        mouse_x = event.xdata
        if mouse_x is None:
            tooltip.set_visible(False)
            vline.set_visible(False)
            fig.canvas.draw_idle()
            return
        if len(d_km) == 0:
            return
        idx = np.argmin(np.abs(d_km - mouse_x))
        if idx >= len(distances):
            return
        dist_val = distances[idx]
        elev_val = terrain_bulge[idx]
        los_val = los_h[idx]
        fresnel_val = fresnel_r[idx]
        clear_val = los_val - fresnel_val - elev_val
        tooltip.set_text(
            "Dist: {:.1f} km\n"
            "Terrain: {:.1f} m\n"
            "LOS: {:.1f} m\n"
            "Fresnel R: {:.1f} m\n"
            "Clearance: {:.1f} m".format(
                dist_val / 1000, elev_val, los_val, fresnel_val, clear_val
            )
        )
        tooltip.set_visible(True)
        vline.set_visible(True)
        vline.set_xdata([mouse_x, mouse_x])
        tooltip_x = mouse_x
        if tooltip_x > (d_km[-1] + d_km[0]) / 2:
            tooltip_x = mouse_x - (d_km[-1] - d_km[0]) * 0.15
        else:
            tooltip_x = mouse_x + (d_km[-1] - d_km[0]) * 0.02
        y_pos = max(elev_val, los_val) + 3
        tooltip.set_position((tooltip_x, y_pos))
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_motion)

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(toolbar)
    layout.addWidget(canvas)

    dock.setWidget(container)
    qgis_iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)