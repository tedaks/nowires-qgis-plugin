# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Internal P2P output helpers: vector layer writing and report file output."""

import os

from NoWires.report_export import write_report_csv, write_report_json, write_report_html
from NoWires.report_markers import write_p2p_marker_layer
from NoWires.p2p_outputs import write_profile_line, write_fresnel_zone


def _write_p2p_output_layers(srs, paths, tx_lat, tx_lon, rx_lat, rx_lon,
        dist_m, result, dist_arr, terrain_bulge, los_h, fresnel_r,
        tx_h, rx_h, tx_gain, rx_gain, tx_power, rx_sens, itm_loss_db=None):
    profile_path = (
        paths["profile_dest"] or os.path.join(paths["temp_dir"], "profile_line.shp"))
    write_profile_line(profile_path, srs, tx_lat, tx_lon, rx_lat, rx_lon, dist_m, result,
                       itm_loss_db=itm_loss_db)
    fresnel_poly_path = (
        paths["fresnel_dest"] or os.path.join(paths["temp_dir"], "fresnel_zone.shp"))
    markers_path = (
        paths["markers_dest"] or os.path.join(paths["temp_dir"], "p2p_markers.shp"))
    _poly_root, _poly_ext = os.path.splitext(fresnel_poly_path)
    fresnel_lines_path = "{}_lines{}".format(_poly_root, _poly_ext)
    write_fresnel_zone(fresnel_poly_path, fresnel_lines_path, srs,
        tx_lat, tx_lon, rx_lat, rx_lon,
        dist_arr, terrain_bulge, los_h, fresnel_r, dist_m)
    write_p2p_marker_layer(markers_path,
        tx_lat=tx_lat, tx_lon=tx_lon, rx_lat=rx_lat, rx_lon=rx_lon,
        tx_h=tx_h, rx_h=rx_h, tx_gain=tx_gain, rx_gain=rx_gain,
        tx_power_dbm=tx_power, rx_sensitivity_dbm=rx_sens)
    return profile_path, fresnel_poly_path, fresnel_lines_path, markers_path


def _write_p2p_reports(report_csv_path, report_json_path, report_html_path,
        report_payload):
    if report_csv_path:
        write_report_csv(report_csv_path, report_payload)
    if report_json_path:
        write_report_json(report_json_path, report_payload)
    if report_html_path:
        write_report_html(report_html_path, report_payload, title="NoWires P2P Report")