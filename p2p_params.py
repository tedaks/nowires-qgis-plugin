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


Parameter definitions for the Point-to-Point radio link analysis algorithm.
"""

from qgis.core import (
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
)
from .radio import (
    ITM_MAX_FREQUENCY_MHZ,
    ITM_MAX_N0,
    ITM_MAX_TERMINAL_HEIGHT_M,
    ITM_MIN_FREQUENCY_MHZ,
    ITM_MIN_N0,
    ITM_MIN_SIGMA,
    ITM_MIN_TERMINAL_HEIGHT_M,
)
from .antenna import ANTENNA_PRESET_OPTIONS
from .clutter import CLUTTER_MODEL_OPTIONS, CLUTTER_OVERRIDE_OPTIONS

__all__ = [
    "PARAM_CONSTANTS",
    "POLARIZATION_NAMES",
    "K_FACTOR_PRESETS_OPTIONS",
    "add_p2p_params",
    "_install_constants",
    "report_p2p_results",
]

PARAM_CONSTANTS = {
    "TX_POINT": "TX_POINT",
    "RX_POINT": "RX_POINT",
    "TX_HEIGHT": "TX_HEIGHT",
    "RX_HEIGHT": "RX_HEIGHT",
    "FREQ_MHZ": "FREQ_MHZ",
    "POLARIZATION": "POLARIZATION",
    "CLIMATE": "CLIMATE",
    "TIME_PCT": "TIME_PCT",
    "LOCATION_PCT": "LOCATION_PCT",
    "SITUATION_PCT": "SITUATION_PCT",
    "TX_POWER": "TX_POWER",
    "TX_GAIN": "TX_GAIN",
    "RX_GAIN": "RX_GAIN",
    "CABLE_LOSS": "CABLE_LOSS",
    "RX_SENSITIVITY": "RX_SENSITIVITY",
    "TX_ANTENNA_PRESET": "TX_ANTENNA_PRESET",
    "TX_ANTENNA_AZ": "TX_ANTENNA_AZ",
    "TX_FRONT_BACK_DB": "TX_FRONT_BACK_DB",
    "TX_DOWNTILT_DEG": "TX_DOWNTILT_DEG",
    "TX_H_PATTERN": "TX_H_PATTERN",
    "TX_V_PATTERN": "TX_V_PATTERN",
    "RX_ANTENNA_PRESET": "RX_ANTENNA_PRESET",
    "RX_ANTENNA_AZ": "RX_ANTENNA_AZ",
    "RX_FRONT_BACK_DB": "RX_FRONT_BACK_DB",
    "RX_DOWNTILT_DEG": "RX_DOWNTILT_DEG",
    "RX_H_PATTERN": "RX_H_PATTERN",
    "RX_V_PATTERN": "RX_V_PATTERN",
    "CLUTTER_MODEL": "CLUTTER_MODEL",
    "CLUTTER_RASTER": "CLUTTER_RASTER",
    "TX_CLUTTER_OVERRIDE": "TX_CLUTTER_OVERRIDE",
    "RX_CLUTTER_OVERRIDE": "RX_CLUTTER_OVERRIDE",
    "K_FACTOR_PRESET": "K_FACTOR_PRESET",
    "K_FACTOR": "K_FACTOR",
    "N0": "N0",
    "EPSILON": "EPSILON",
    "SIGMA": "SIGMA",
    "OUTPUT_PROFILE": "OUTPUT_PROFILE",
    "OUTPUT_FRESNEL": "OUTPUT_FRESNEL",
    "OUTPUT_MARKERS": "OUTPUT_MARKERS",
    "OUTPUT_REPORT_CSV": "OUTPUT_REPORT_CSV",
    "OUTPUT_REPORT_JSON": "OUTPUT_REPORT_JSON",
    "OUTPUT_REPORT_HTML": "OUTPUT_REPORT_HTML",
    "SHOW_CHART": "SHOW_CHART",
}

POLARIZATION_NAMES = {0: "Horizontal", 1: "Vertical"}

K_FACTOR_PRESETS_OPTIONS = [
    "0.67 - Sub-refractive",
    "1.00 - Geometric",
    "1.33 - Standard atmosphere",
    "2.00 - Super-refractive",
    "4.00 - Strong super-refractive",
    "Custom",
]


def _install_constants(cls, constants_dict):
    for key, value in constants_dict.items():
        setattr(cls, key, value)


def add_p2p_params(algorithm):
    algorithm.addParameter(
        QgsProcessingParameterPoint(algorithm.TX_POINT, "Transmitter (TX) point")
    )
    algorithm.addParameter(
        QgsProcessingParameterPoint(algorithm.RX_POINT, "Receiver (RX) point")
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.TX_HEIGHT,
            "TX antenna height (m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=30.0,
            minValue=ITM_MIN_TERMINAL_HEIGHT_M,
            maxValue=ITM_MAX_TERMINAL_HEIGHT_M,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.RX_HEIGHT,
            "RX antenna height (m)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=ITM_MIN_TERMINAL_HEIGHT_M,
            maxValue=ITM_MAX_TERMINAL_HEIGHT_M,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.FREQ_MHZ,
            "Frequency (MHz)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=300.0,
            minValue=ITM_MIN_FREQUENCY_MHZ,
            maxValue=ITM_MAX_FREQUENCY_MHZ,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            algorithm.POLARIZATION,
            "Polarization",
            options=["Horizontal", "Vertical"],
            defaultValue=1,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            algorithm.CLIMATE,
            "Climate zone",
            options=[
                "Equatorial",
                "Continental Subtropical",
                "Maritime Subtropical",
                "Desert",
                "Continental Temperate",
                "Maritime Temperate (land)",
                "Maritime Temperate (sea)",
            ],
            defaultValue=1,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.TIME_PCT,
            "Time percentage",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=50.0,
            minValue=0.01,
            maxValue=99.99,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.LOCATION_PCT,
            "Location percentage",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=50.0,
            minValue=0.01,
            maxValue=99.99,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.SITUATION_PCT,
            "Situation percentage",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=50.0,
            minValue=0.01,
            maxValue=99.99,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.TX_POWER,
            "TX power (dBm)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=43.0,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.TX_GAIN,
            "TX antenna gain (dBi)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=8.0,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.RX_GAIN,
            "RX antenna gain (dBi)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=2.0,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.CABLE_LOSS,
            "Cable loss (dB)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=2.0,
            minValue=0.0,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterNumber(
            algorithm.RX_SENSITIVITY,
            "RX sensitivity (dBm)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=-100.0,
        )
    )
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.TX_ANTENNA_PRESET, "TX antenna preset",
        options=ANTENNA_PRESET_OPTIONS, defaultValue=0,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.TX_ANTENNA_AZ, "TX antenna azimuth (deg)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.TX_FRONT_BACK_DB, "TX front-to-back ratio (dB)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=25.0, minValue=0.0,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.TX_DOWNTILT_DEG, "TX downtilt (deg)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=0.0, minValue=-45.0, maxValue=45.0,
    ))
    algorithm.addParameter(QgsProcessingParameterFile(
        algorithm.TX_H_PATTERN, "TX horizontal pattern CSV",
        extension="csv", optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterFile(
        algorithm.TX_V_PATTERN, "TX vertical pattern CSV",
        extension="csv", optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.RX_ANTENNA_PRESET, "RX antenna preset",
        options=ANTENNA_PRESET_OPTIONS, defaultValue=0,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.RX_ANTENNA_AZ, "RX antenna azimuth (deg)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=0.0, minValue=0.0, maxValue=360.0, optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.RX_FRONT_BACK_DB, "RX front-to-back ratio (dB)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=25.0, minValue=0.0,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        algorithm.RX_DOWNTILT_DEG, "RX downtilt (deg)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=0.0, minValue=-45.0, maxValue=45.0,
    ))
    algorithm.addParameter(QgsProcessingParameterFile(
        algorithm.RX_H_PATTERN, "RX horizontal pattern CSV",
        extension="csv", optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterFile(
        algorithm.RX_V_PATTERN, "RX vertical pattern CSV",
        extension="csv", optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.CLUTTER_MODEL, "Clutter correction",
        options=CLUTTER_MODEL_OPTIONS, defaultValue=0,
    ))
    algorithm.addParameter(QgsProcessingParameterFile(
        algorithm.CLUTTER_RASTER, "Land-cover raster (auto-downloaded if blank)",
        extension="tif", optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.TX_CLUTTER_OVERRIDE, "TX clutter override",
        options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0,
    ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        algorithm.RX_CLUTTER_OVERRIDE, "RX clutter override",
        options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0,
    ))
    algorithm.addParameter(
        QgsProcessingParameterEnum(
            algorithm.K_FACTOR_PRESET,
            "Earth radius factor preset (k)",
            options=K_FACTOR_PRESETS_OPTIONS,
            defaultValue=2,
        )
    )
    k_factor_param = QgsProcessingParameterNumber(
        algorithm.K_FACTOR,
        "Custom Earth radius factor (k)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=4.0 / 3.0,
        minValue=0.1,
    )
    k_factor_param.setFlags(
        k_factor_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
    )
    algorithm.addParameter(k_factor_param)
    n0_param = QgsProcessingParameterNumber(
        algorithm.N0,
        "Surface refractivity N0 (N-units)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=301.0,
        minValue=ITM_MIN_N0,
        maxValue=ITM_MAX_N0,
    )
    n0_param.setFlags(n0_param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
    algorithm.addParameter(n0_param)

    epsilon_param = QgsProcessingParameterNumber(
        algorithm.EPSILON,
        "Earth permittivity (epsilon)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=15.0,
        minValue=1.0,
    )
    epsilon_param.setFlags(
        epsilon_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
    )
    algorithm.addParameter(epsilon_param)

    sigma_param = QgsProcessingParameterNumber(
        algorithm.SIGMA,
        "Earth conductivity (sigma, S/m)",
        type=QgsProcessingParameterNumber.Double,
        defaultValue=0.005,
        minValue=ITM_MIN_SIGMA,
    )
    sigma_param.setFlags(
        sigma_param.flags() | QgsProcessingParameterNumber.FlagAdvanced
    )
    algorithm.addParameter(sigma_param)

    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            algorithm.OUTPUT_PROFILE, "Profile line output", "GeoPackage files (*.gpkg)"
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            algorithm.OUTPUT_FRESNEL, "Fresnel zone polygon", "GeoPackage files (*.gpkg)"
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            algorithm.OUTPUT_MARKERS, "TX/RX marker output", "GeoPackage files (*.gpkg)"
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            algorithm.OUTPUT_REPORT_CSV,
            "P2P report CSV",
            "CSV files (*.csv)",
            optional=True,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            algorithm.OUTPUT_REPORT_JSON,
            "P2P report JSON",
            "JSON files (*.json)",
            optional=True,
        )
    )
    algorithm.addParameter(
        QgsProcessingParameterFileDestination(
            algorithm.OUTPUT_REPORT_HTML,
            "P2P report HTML",
            "HTML files (*.html)",
            optional=True,
        )
    )

    algorithm.addParameter(
        QgsProcessingParameterBoolean(
            algorithm.SHOW_CHART,
            "Show profile chart after analysis",
            defaultValue=True,
            optional=False,
        )
    )


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