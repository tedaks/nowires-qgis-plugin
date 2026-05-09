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


Coverage Comparison Algorithm — Output helpers.

Standalone functions for writing rasters, applying styles, and generating
HTML comparison reports.
"""

from qgis.core import (
    QgsColorRampShader,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)

from .raster_io import write_geotiff

__all__ = [
    "write_coverage_raster",
    "write_delta_raster",
    "apply_delta_style",
    "write_comparison_html_report",
    "compute_delta_summary",
]


def write_coverage_raster(tif_path, prx_grid, min_lat, max_lat, min_lon, max_lon, rx_sens):
    """Write a coverage raster to GeoTIFF."""
    write_geotiff(tif_path, prx_grid, min_lat, max_lat, min_lon, max_lon)


def write_delta_raster(tif_path, delta_grid, min_lat, max_lat, min_lon, max_lon):
    """Write the delta (A-B) raster to GeoTIFF."""
    write_geotiff(tif_path, delta_grid, min_lat, max_lat, min_lon, max_lon)


def apply_delta_style(layer, threshold_db, style="diverging"):
    """Apply color ramp to delta raster. 'diverging' uses blue-white-red;
    'threshold' shows only three categories: improved, unchanged, degraded."""
    from qgis.PyQt.QtGui import QColor

    provider = layer.dataProvider()
    entries = []

    if style == "threshold":
        entries = [
            QgsColorRampShader.ColorRampItem(
                -1e6, QColor(30, 80, 180), f"A better (<-{threshold_db:.0f} dB)"
            ),
            QgsColorRampShader.ColorRampItem(
                -threshold_db, QColor(30, 80, 180), f"A better (<-{threshold_db:.0f} dB)"
            ),
            QgsColorRampShader.ColorRampItem(
                -threshold_db + 0.001, QColor(240, 240, 240), "No change"
            ),
            QgsColorRampShader.ColorRampItem(
                threshold_db - 0.001, QColor(240, 240, 240), "No change"
            ),
            QgsColorRampShader.ColorRampItem(
                threshold_db, QColor(180, 30, 30), f"A worse (>+{threshold_db:.0f} dB)"
            ),
            QgsColorRampShader.ColorRampItem(
                1e6, QColor(180, 30, 30), f"A worse (>+{threshold_db:.0f} dB)"
            ),
        ]
    else:
        entries = [
            QgsColorRampShader.ColorRampItem(
                -threshold_db * 2, QColor(30, 80, 180, 200), f"A better (<-{threshold_db:.0f} dB)"
            ),
            QgsColorRampShader.ColorRampItem(
                -threshold_db, QColor(80, 150, 220, 210), f"-{threshold_db:.0f} dB"
            ),
            QgsColorRampShader.ColorRampItem(
                0.0, QColor(255, 255, 255, 255), "No change"
            ),
            QgsColorRampShader.ColorRampItem(
                threshold_db, QColor(220, 150, 80, 210), f"+{threshold_db:.0f} dB"
            ),
            QgsColorRampShader.ColorRampItem(
                threshold_db * 2, QColor(180, 30, 30, 200), f"A worse (>+{threshold_db:.0f} dB)"
            ),
        ]

    color_ramp_shader = QgsColorRampShader()
    if style != "threshold":
        color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
    color_ramp_shader.setColorRampItemList(entries)

    shader = QgsRasterShader()
    shader.setRasterShaderFunction(color_ramp_shader)

    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
    layer.setRenderer(renderer)
    layer.triggerRepaint()


def write_comparison_html_report(path, panel_a_info, panel_b_info, delta_info):
    """Write an HTML comparison report."""
    import html

    panel_a = panel_a_info
    panel_b = panel_b_info
    delta = delta_info

    rows = []
    for panel, label in [(panel_a, "Panel A"), (panel_b, "Panel B")]:
        rows.append(f"<h3>{label}</h3>")
        rows.append("<table>")
        rows.append(f"<tr><th>TX Location</th><td>{panel['tx_lat']:.5f}, {panel['tx_lon']:.5f}</td></tr>")
        rows.append(f"<tr><th>TX Height</th><td>{panel['tx_h']:.1f} m</td></tr>")
        rows.append(f"<tr><th>RX Height</th><td>{panel['rx_h']:.1f} m</td></tr>")
        rows.append(f"<tr><th>Frequency</th><td>{panel['f_mhz']:.1f} MHz</td></tr>")
        rows.append(f"<tr><th>Radius</th><td>{panel['radius_km']:.1f} km</td></tr>")
        rows.append(f"<tr><th>TX Power</th><td>{panel['tx_power']:.1f} dBm</td></tr>")
        rows.append(f"<tr><th>TX Gain</th><td>{panel['tx_gain']:.1f} dBi</td></tr>")
        rows.append(f"<tr><th>RX Gain</th><td>{panel['rx_gain']:.1f} dBi</td></tr>")
        rows.append(f"<tr><th>Cable Loss</th><td>{panel['cable_loss']:.1f} dB</td></tr>")
        rows.append(f"<tr><th>Valid Pixels</th><td>{panel['valid_pixels']} / {panel['total_pixels']}</td></tr>")
        rows.append(f"<tr><th>Mean Received Power</th><td>{panel['mean_prx']:.1f} dBm</td></tr>")
        rows.append("</table>")

    delta_rows = f"""
        <h3>Delta Summary (A - B)</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><th>Delta Style</th><td>{html.escape(delta['style'])}</td></tr>
            <tr><th>Threshold</th><td>{delta['threshold_db']:.1f} dB</td></tr>
            <tr><th>Valid Delta Pixels</th><td>{delta['valid_pixels']}</td></tr>
            <tr><th>Improved (A better than B)</th><td>{delta['improved_pixels']} ({delta['improved_pct']:.1f}%)</td></tr>
            <tr><th>Degraded (A worse than B)</th><td>{delta['degraded_pixels']} ({delta['degraded_pct']:.1f}%)</td></tr>
            <tr><th>Unchanged</th><td>{delta['unchanged_pixels']} ({delta['unchanged_pct']:.1f}%)</td></tr>
            <tr><th>Min Delta</th><td>{delta['min_delta']:.2f} dB</td></tr>
            <tr><th>Max Delta</th><td>{delta['max_delta']:.2f} dB</td></tr>
            <tr><th>Mean Delta</th><td>{delta['mean_delta']:.2f} dB</td></tr>
        </table>
        """

    document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>NoWires Coverage Comparison Report</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; }}
      h1, h2, h3 {{ margin: 0 0 12px; }}
      section {{ margin: 0 0 20px; }}
      table {{ border-collapse: collapse; width: 100%; max-width: 960px; margin-bottom: 16px; }}
      th, td {{ border: 1px solid #cbd2d9; padding: 8px 10px; text-align: left; }}
      th {{ background: #f5f7fa; width: 32%; }}
      .delta-summary {{ margin: 0 0 20px; padding: 12px; background: #f5f7fa; }}
    </style>
  </head>
  <body>
    <h1>NoWires Coverage Comparison Report</h1>
    <div class="delta-summary">
      <strong>Delta Interpretation:</strong> Positive values indicate Panel A has higher path loss than Panel B (Panel B is better).
      Negative values indicate Panel A has lower path loss than Panel B (Panel A is better).
    </div>
    {''.join(rows)}
    {delta_rows}
  </body>
</html>
"""
    from pathlib import Path
    Path(path).write_text(document, encoding="utf-8")


def compute_delta_summary(loss_grid_a, loss_grid_b, threshold_db):
    import numpy as np
    from .constants import COVERAGE_NODATA

    loss_grid_a = np.where(np.isfinite(loss_grid_a) & (loss_grid_a != COVERAGE_NODATA), loss_grid_a, np.nan)
    loss_grid_b = np.where(np.isfinite(loss_grid_b) & (loss_grid_b != COVERAGE_NODATA), loss_grid_b, np.nan)

    if loss_grid_a.shape != loss_grid_b.shape:
        raise ValueError(
            "Grid shapes do not match: {} vs {}".format(loss_grid_a.shape, loss_grid_b.shape))

    loss_delta_grid = loss_grid_a - loss_grid_b
    valid_mask = ~np.isnan(loss_grid_a) & ~np.isnan(loss_grid_b)
    valid_delta = valid_mask & ~np.isnan(loss_delta_grid)
    valid_count = int(valid_delta.sum())
    total_count = int(valid_mask.sum())

    if valid_count > 0:
        delta_values = loss_delta_grid[valid_delta]
        improved = int((delta_values < -threshold_db).sum())
        degraded = int((delta_values > threshold_db).sum())
        unchanged = valid_count - improved - degraded
        min_delta = float(np.nanmin(delta_values))
        max_delta = float(np.nanmax(delta_values))
        mean_delta = float(np.nanmean(delta_values))
        improved_pct = improved / valid_count * 100
        degraded_pct = degraded / valid_count * 100
        unchanged_pct = unchanged / valid_count * 100
    else:
        improved = degraded = unchanged = 0
        min_delta = max_delta = mean_delta = 0.0
        improved_pct = degraded_pct = unchanged_pct = 0.0

    delta_info = {
        "valid_count": valid_count,
        "total_count": total_count,
        "improved": improved,
        "degraded": degraded,
        "unchanged": unchanged,
        "improved_pixels": improved,
        "degraded_pixels": degraded,
        "unchanged_pixels": unchanged,
        "improved_pct": improved_pct,
        "degraded_pct": degraded_pct,
        "unchanged_pct": unchanged_pct,
        "valid_pixels": valid_count,
        "total_pixels": total_count,
        "min_delta": min_delta,
        "max_delta": max_delta,
        "mean_delta": mean_delta,
        "loss_delta_grid": loss_delta_grid,
        "valid_mask": valid_mask,
        "threshold_db": threshold_db,
        "style": "diverging",
    }
    return delta_info
