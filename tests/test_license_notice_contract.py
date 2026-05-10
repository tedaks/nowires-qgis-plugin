# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""License and attribution documentation contracts."""

from pathlib import Path

from report_payloads import build_coverage_report_payload


PLUGIN_DIR = Path(__file__).resolve().parent.parent


def _text(name):
    return (PLUGIN_DIR / name).read_text(encoding="utf-8")


def test_notice_documents_worldcover_license_and_citation():
    notice = _text("NOTICE.md")

    assert "ESA WorldCover 2020 v100" in notice
    assert "Creative Commons Attribution 4.0 International" in notice
    assert "https://doi.org/10.5281/zenodo.5571936" in notice
    assert "Contains modified Copernicus Sentinel data (2020)" in notice


def test_notice_lists_all_contourlines_derived_modules():
    notice = _text("NOTICE.md")

    for filename in (
        "algorithm_contour.py",
        "dem_downloader.py",
        "contour_generation.py",
        "contour_pipeline.py",
        "contour_symbology.py",
        "contour_overlay.py",
        "contour_smoothing.py",
    ):
        assert f"`{filename}`" in notice


def test_notice_preserves_nowires_mit_copyright():
    notice = _text("NOTICE.md")

    assert "Copyright (c) 2024 NoWires Contributors" in notice
    assert "**Copyright:** Copyright (c) 2024 NoWires Contributors" in notice


def test_notice_includes_full_ntia_risk_disclaimer():
    notice = _text("NOTICE.md")

    assert "You are solely responsible for determining the appropriateness" in notice
    assert "This software is not intended to be used in any situation" in notice


def test_notice_documents_logo_asset_origin():
    notice = _text("NOTICE.md")

    assert "logo.png" in notice
    assert "Original NoWires project artwork" in notice


def test_python_sources_have_machine_readable_spdx_header():
    missing = []
    for path in sorted(PLUGIN_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        header = "\n".join(path.read_text(encoding="utf-8").splitlines()[:8])
        if "SPDX-License-Identifier:" not in header:
            missing.append(path.relative_to(PLUGIN_DIR).as_posix())

    assert missing == []


def test_worldcover_attribution_is_included_in_report_payloads_when_used():
    payload = build_coverage_report_payload(
        tx_lat=14.0, tx_lon=121.0, tx_h=30.0, rx_h=10.0, f_mhz=900.0,
        radius_km=5.0, grid_size=64, polarization_name="Horizontal",
        climate_name="Continental Temperate", time_pct=50.0,
        location_pct=50.0, situation_pct=50.0, tx_power=30.0,
        tx_gain=10.0, rx_gain=0.0, cable_loss=1.0, rx_sensitivity_dbm=-90.0,
        valid_pixel_count=10, pixel_count=64, min_prx_dbm=-100.0,
        max_prx_dbm=-60.0, mean_prx_dbm=-80.0, pct_above_sensitivity=50.0,
        usable_cell_count=5, min_distance_km=0.1, max_distance_km=2.0,
        average_distance_km=1.0, clutter_model="Simple clutter correction",
        clutter_source="/tmp/NoWires-user/nowires_worldcover_run/merged_worldcover.tif",
    )

    assert "attribution" in payload
    assert "esa_worldcover" in payload["attribution"]
    assert "Contains modified Copernicus Sentinel data (2020)" in (
        payload["attribution"]["esa_worldcover"]
    )
