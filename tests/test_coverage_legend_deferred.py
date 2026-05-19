# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for the deferred coverage-legend show.

With ALLOW_THREADING=True on CoverageAlgorithm, processAlgorithm runs on a
QThreadPool worker. Cocoa rejects QWidget creation off the main thread, so
the legend show must be deferred to postProcessAlgorithm. Source-level
contract checks here so we don't regress without QGIS UI testing.
"""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_coverage_does_not_show_legend_inside_process_algorithm():
    """No direct show_coverage_legend(...) call inside _write_coverage_outputs
    or processAlgorithm — must be deferred to postProcessAlgorithm.
    """
    src = _source("algorithm/coverage.py")
    # _write_coverage_outputs writes to _pending_legend_rx_sens; the actual
    # show() happens later, on the main thread.
    assert "show_coverage_legend(rx_sensitivity_dbm=p.rx_sens)" not in src
    assert "_pending_legend_rx_sens = p.rx_sens" in src


def test_coverage_post_process_shows_legend():
    src = _source("algorithm/coverage.py")
    assert "def postProcessAlgorithm" in src
    # postProcessAlgorithm must call show_coverage_legend when pending.
    assert "show_coverage_legend(rx_sensitivity_dbm=rx)" in src


def test_coverage_legend_import_present():
    src = _source("algorithm/coverage.py")
    assert "from NoWires.coverage.legend import show_coverage_legend" in src
