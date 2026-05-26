# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: coverage params must have omni preset guard for BW/AZ."""

import os


def test_coverage_params_has_omni_guard():
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "radio_coverage", "params.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()
    assert "if antenna_preset == 0:" in source
    assert "antenna_az = None" in source
    assert "antenna_bw_override" in source


def test_comparison_params_omni_guard_still_present():
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "comparison", "params.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()
    assert "if antenna_preset == 0:" in source
    assert "antenna_bw_override = 360.0" in source
