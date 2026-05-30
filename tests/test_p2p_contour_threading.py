# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: P2P and Contour algorithms must opt into threading.

After the v1.7.1 fix, both P2P and Contour set ALLOW_THREADING = True and
defer Qt widget creation (show_profile_chart) to postProcessAlgorithm.
"""

import os

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_p2p_allows_threading():
    src = _source("algorithm/p2p.py")
    assert "ALLOW_THREADING = True" in src


def test_contour_allows_threading():
    src = _source("algorithm/contour.py")
    assert "ALLOW_THREADING = True" in src


def test_p2p_defers_chart_to_postprocess():
    src = _source("algorithm/p2p.py")
    assert "postProcessAlgorithm" in src
    assert "show_profile_chart" in src


def test_p2p_chart_kwargs_stored_on_params():
    src = _source("p2p/analysis_params.py")
    assert "_pending_chart_kwargs" in src