# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: post-processing must use context.project() instead of QgsProject.instance().

Ensures base_algorithm.py postProcessAlgorithm and
processing_utils.queue_layer_for_loading prefer the context project over the
singleton, falling back only when no context project is available.
"""

import os

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_base_algorithm_postprocess_uses_context_project():
    src = _source("base_algorithm.py")
    assert "context.project()" in src
    assert 'QgsProject.instance().layerTreeRoot()' not in src
    assert 'QgsProject.instance().writeEntry(' not in src


def test_queue_layer_for_loading_resolves_project_from_context():
    src = _source("processing_utils.py")
    assert "context.project()" in src


def test_three_d_highlight_accepts_project_param():
    src = _source("three_d.py")
    assert "def highlight_nowires_layers(iface, project=None)" in src


def test_three_d_open_view_accepts_project_param():
    src = _source("three_d.py")
    assert "def open_nowires_3d_view(iface, scene_mode=SCENE_MODE_LOCAL, project=None)" in src