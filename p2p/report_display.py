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

Display helpers for Point-to-Point radio link analysis results.
"""

__all__ = ["report_p2p_results"]


def report_p2p_results(feedback, dist_m, f_mhz, result, report_payload,
                        k_factor, los_blocked, fresnel_r_max):
    pld = report_payload
    inputs = pld["inputs"]
    results = pld["results"]
    tx_power = inputs["tx_power_dbm"]
    tx_gain = inputs["tx_gain_dbi"]
    cable_loss = inputs["cable_loss_db"]
    eirp_dbm = results["eirp_dbm"]
    fspl_db = results["free_space_loss_db"]
    total_path_loss_db = results["total_path_loss_db"]
    antenna_gain_adjustment_db_total = results["antenna_gain_adjustment_db"]
    rx_gain = inputs["rx_gain_dbi"]
    prx_dbm = results["received_power_dbm"]
    rx_sens = inputs["rx_sensitivity_dbm"]
    margin_db = results["link_margin_db"]
    clutter_tx_db = results["clutter_tx_db"]
    clutter_rx_db = results["clutter_rx_db"]
    mode_name = results["propagation_mode_name"]
    f1_violated = results["fresnel_1_violated"]
    f60_violated = results["fresnel_60_violated"]
    feedback.pushInfo("")
    feedback.pushInfo("=" * 50)
    feedback.pushInfo("P2P ANALYSIS RESULTS")
    feedback.pushInfo("=" * 50)
    feedback.pushInfo(
        "Distance: {:.1f} m ({:.2f} km)".format(dist_m, dist_m / 1000)
    )
    feedback.pushInfo("Frequency: {:.1f} MHz".format(f_mhz))
    climate_name = inputs.get("climate", "")
    if climate_name:
        feedback.pushInfo("Climate: {}".format(climate_name))
    feedback.pushInfo(
        "Propagation mode: {} ({})".format(result.mode, mode_name)
    )
    feedback.pushInfo("")
    feedback.pushInfo("LINK BUDGET")
    feedback.pushInfo("  TX Power:       {:.2f} dBm".format(tx_power))
    feedback.pushInfo("  TX Gain:        {:.2f} dBi".format(tx_gain))
    feedback.pushInfo("  Cable Loss:     {:.2f} dB".format(cable_loss))
    feedback.pushInfo("  EIRP:           {:.2f} dBm".format(eirp_dbm))
    itm_loss_db = results["itm_loss_db"]
    feedback.pushInfo("  Free Space Loss:{:.2f} dB".format(fspl_db))
    feedback.pushInfo("  ITM Path Loss:  {:.2f} dB".format(itm_loss_db))
    feedback.pushInfo("  Clutter TX Loss:{:.2f} dB".format(clutter_tx_db))
    feedback.pushInfo("  Clutter RX Loss:{:.2f} dB".format(clutter_rx_db))
    feedback.pushInfo("  Total Path Loss:{:.2f} dB".format(total_path_loss_db))
    feedback.pushInfo("  Antenna Pattern:{:.2f} dB".format(antenna_gain_adjustment_db_total))
    feedback.pushInfo(
        "  Excess Loss:    {:.2f} dB".format(itm_loss_db - fspl_db)
    )
    feedback.pushInfo("  RX Gain:        {:.2f} dBi".format(rx_gain))
    feedback.pushInfo("  Received Power: {:.2f} dBm".format(prx_dbm))
    feedback.pushInfo("  RX Sensitivity: {:.2f} dBm".format(rx_sens))
    feedback.pushInfo("  Link Margin:    {:.2f} dB".format(margin_db))
    feedback.pushInfo(
        "  Fade Margin Class: {}".format(results["fade_margin_class"])
    )
    feedback.pushInfo(
        "  Reliability:     {}".format(results["reliability_summary"])
    )
    feedback.pushInfo(
        "  Availability Method: {}".format(results["availability_method"])
    )
    if results["availability_estimate_pct"] is not None:
        feedback.pushInfo(
            "  Availability Estimate: {:.2f}%".format(
                results["availability_estimate_pct"]
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
