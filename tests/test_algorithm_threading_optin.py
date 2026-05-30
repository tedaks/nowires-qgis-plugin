# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contract tests for the ALLOW_THREADING opt-in on heavy-compute algorithms.

Source-level checks: avoid needing a QGIS runtime so these run in the unit
suite. Heavy-compute algorithms must opt their processAlgorithm() into the
worker-thread runner so the QGIS UI stays responsive.
"""

import os


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_base_algorithm_defaults_threading_off():
    src = _source("base_algorithm.py")
    assert "ALLOW_THREADING = False" in src
    # The default flag application path must still set NoThreading.
    assert "f |= Qgis.ProcessingAlgorithmFlag.NoThreading" in src


def test_coverage_algorithm_opts_into_threading():
    assert "ALLOW_THREADING = True" in _source("algorithm/coverage.py")


def test_batch_algorithm_opts_into_threading():
    assert "ALLOW_THREADING = True" in _source("algorithm/batch.py")


def test_coverage_comparison_algorithm_opts_into_threading():
    assert "ALLOW_THREADING = True" in _source("algorithm/coverage_comparison.py")


def test_p2p_and_contour_opt_into_threading():
    for name in ("algorithm/p2p.py", "algorithm/contour.py"):
        assert "ALLOW_THREADING = True" in _source(name), name
