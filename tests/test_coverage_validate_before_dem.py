# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: coverage algorithm must call validate_itm_input_ranges before DEM download.

Ensures the coverage algorithm validates inputs fail-fast before the potentially
long DEM download.
"""

import os

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_coverage_validates_before_dem_download():
    src = _source("algorithm/coverage.py")
    validate_call_pos = src.find("validate_itm_input_ranges(\n")
    if validate_call_pos == -1:
        validate_call_pos = src.find("validate_itm_input_ranges(")
    dem_call_pos = src.find("ensure_dem_for_area(")
    assert validate_call_pos != -1, "coverage algorithm must call validate_itm_input_ranges"
    assert dem_call_pos != -1, "coverage algorithm must call ensure_dem_for_area"
    assert validate_call_pos < dem_call_pos, (
        "validate_itm_input_ranges must be called before ensure_dem_for_area"
    )


def test_coverage_passes_extended_validation_params():
    src = _source("algorithm/coverage.py")
    assert "time_pct=p.time_pct" in src
    assert "location_pct=p.location_pct" in src
    assert "situation_pct=p.situation_pct" in src
    assert "epsilon=p.epsilon" in src