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

Display helpers for Point-to-Point radio link analysis results.
"""

__all__ = ["report_p2p_results"]


def report_p2p_results(
    feedback, dist_m, f_mhz, result, PROP_MODE_NAMES,
    tx_power, tx_gain, cable_loss, eirp_dbm, fspl_db,
    clutter_losses, total_path_loss_db, antenna_gain_adjustment_db_total,
    rx_gain, prx_dbm, rx_sens, margin_db, report_payload,
    k_factor, los_blocked, f1_violated, f60_violated, fresnel_r_max,
):
    feedback.pushInfo("")
    feedback.pushInfo("=" * 50)
    feedback.pushInfo("P2P ANALYSIS RESULTS")
    feedback.pushInfo("=" * 50)
    feedback.pushInfo(
        "Distance: {:.1f} m ({:.2f} km)".format(dist_m, dist_m / 1000)
    )
    feedback.pushInfo("Frequency: {:.1f} MHz".format(f_mhz))
    feedback.pushInfo(
        "Propagation mode: {} ({})".format(
            result.mode, PROP_MODE_NAMES.get(result.mode, "Unknown")
        )
    )
    feedback.pushInfo("")
    feedback.pushInfo("LINK BUDGET")
    feedback.pushInfo("  TX Power:       {:.2f} dBm".format(tx_power))
    feedback.pushInfo("  TX Gain:        {:.2f} dBi".format(tx_gain))
    feedback.pushInfo("  Cable Loss:     {:.2f} dB".format(cable_loss))
    feedback.pushInfo("  EIRP:           {:.2f} dBm".format(eirp_dbm))
    feedback.pushInfo("  Free Space Loss:{:.2f} dB".format(fspl_db))
    feedback.pushInfo("  ITM Path Loss:  {:.2f} dB".format(result.loss_db))
    feedback.pushInfo("  Clutter TX Loss:{:.2f} dB".format(clutter_losses.tx_loss_db))
    feedback.pushInfo("  Clutter RX Loss:{:.2f} dB".format(clutter_losses.rx_loss_db))
    feedback.pushInfo("  Total Path Loss:{:.2f} dB".format(total_path_loss_db))
    feedback.pushInfo("  Antenna Pattern:{:.2f} dB".format(antenna_gain_adjustment_db_total))
    feedback.pushInfo(
        "  Excess Loss:    {:.2f} dB".format(result.loss_db - fspl_db)
    )
    feedback.pushInfo("  RX Gain:        {:.2f} dBi".format(rx_gain))
    feedback.pushInfo("  Received Power: {:.2f} dBm".format(prx_dbm))
    feedback.pushInfo("  RX Sensitivity: {:.2f} dBm".format(rx_sens))
    feedback.pushInfo("  Link Margin:    {:.2f} dB".format(margin_db))
    feedback.pushInfo(
        "  Fade Margin Class: {}".format(
            report_payload["results"]["fade_margin_class"]
        )
    )
    feedback.pushInfo(
        "  Reliability:     {}".format(
            report_payload["results"]["reliability_summary"]
        )
    )
    feedback.pushInfo(
        "  Availability Method: {}".format(
            report_payload["results"]["availability_method"]
        )
    )
    if report_payload["results"]["availability_estimate_pct"] is not None:
        feedback.pushInfo(
            "  Availability Estimate: {:.2f}%".format(
                report_payload["results"]["availability_estimate_pct"]
            )
        )
    feedback.pushInfo("")
    feedback.pushInfo("FRESNEL ZONE ANALYSIS (k={:.3f})".format(k_factor))
    feedback.pushInfo(
        "  LOS Blocked:         {}".format("YES" if los_blocked else "NO")
    )
    feedback.pushInfo(
        "  1st Fresnel violated: {}".format("YES" if f1_violated else "NO")
    )
    feedback.pushInfo(
        "  60% Fresnel rule violated: {}".format("YES" if f60_violated else "NO")
    )
    feedback.pushInfo(
        "  Max 1st Fresnel radius: {:.1f} m".format(fresnel_r_max)
    )
    feedback.pushInfo("")
    if margin_db >= 0:
        feedback.pushInfo(
            "LINK STATUS: VIABLE (margin {:.1f} dB above sensitivity)".format(
                margin_db
            )
        )
    else:
        feedback.pushInfo(
            "LINK STATUS: NOT VIABLE (margin {:.1f} dB below sensitivity)".format(
                margin_db
            )
        )
    feedback.pushInfo("=" * 50)