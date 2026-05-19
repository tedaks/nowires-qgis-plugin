# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for provider and menu wiring."""

import os
import configparser


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")
PROVIDER_SOURCE = os.path.join(PLUGIN_DIR, "provider.py")
PLUGIN_SOURCE = os.path.join(PLUGIN_DIR, "nowires.py")
README_SOURCE = os.path.join(PLUGIN_DIR, "README.md")
METADATA_SOURCE = os.path.join(PLUGIN_DIR, "metadata.txt")


def _text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def test_provider_does_not_register_radius_algorithm():
    assert "CoverageRadiusAlgorithm" not in _text(PROVIDER_SOURCE)


def test_plugin_menu_uses_single_coverage_action():
    source = _text(PLUGIN_SOURCE)
    assert '"Coverage Analysis"' in source
    assert "Coverage Radius Sweep" not in source
    assert 'processing.execAlgorithmDialog("nowires:coverage_analysis")' in source


def test_docs_describe_coverage_analysis_only():
    assert "Coverage Analysis" in _text(README_SOURCE)
    assert "Coverage Radius Sweep" not in _text(README_SOURCE)
    assert "Coverage Analysis" in _text(METADATA_SOURCE)


def test_metadata_targets_qgis4_only():
    parser = configparser.ConfigParser()
    parser.read(METADATA_SOURCE)
    assert parser["general"]["qgisMinimumVersion"].startswith("4")


def test_metadata_about_mentions_qgis4_qt6_target():
    parser = configparser.ConfigParser()
    parser.read(METADATA_SOURCE)
    about = parser["general"]["about"]
    assert "QGIS 4" in about
    assert "Qt 6" in about


def test_plugin_unload_clears_coverage_legend():
    source = _text(PLUGIN_SOURCE)
    assert "from NoWires.coverage_legend import remove_coverage_legend" in source
    assert "remove_coverage_legend()" in source


def test_plugin_unload_guards_missing_provider():
    source = _text(PLUGIN_SOURCE)
    assert "if self.provider is not None:" in source
    assert "removeProvider(self.provider)" in source
    assert "self.provider = None" in source


def test_provider_registers_batch_algorithm():
    assert "BatchAnalysisAlgorithm" in _text(PROVIDER_SOURCE)


def test_provider_registers_comparison_algorithm():
    assert "CoverageComparisonAlgorithm" in _text(PROVIDER_SOURCE)


def test_plugin_menu_has_batch_action():
    source = _text(PLUGIN_SOURCE)
    # The action_specs list registers both comparison and batch menu actions.
    assert '"Coverage Comparison"' in source
    assert '"Batch P2P Analysis"' in source


def test_plugin_toolbar_includes_batch_and_comparison():
    source = _text(PLUGIN_SOURCE)
    assert "_toolbar_actions" in source
    assert '"Coverage Comparison"' in source
    assert '"Batch P2P Analysis"' in source
    assert "addToolBarIcon" in source
