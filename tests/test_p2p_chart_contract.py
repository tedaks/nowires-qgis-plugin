# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Contract tests for p2p_chart module.

p2p_chart.py depends heavily on matplotlib and QGIS Qt, so we test
import-level invariants and the pure data-preparation parts only.
"""



class TestP2pChartModuleContract:
    def test_module_imports(self):
        from NoWires.p2p.chart import show_profile_chart
        from NoWires.p2p.chart_helpers import add_obstruction_annotations, setup_tooltip
        assert callable(show_profile_chart)
        assert callable(add_obstruction_annotations)
        assert callable(setup_tooltip)

    def test_all_declared_exports(self):
        from NoWires.p2p import chart as p2p_chart
        assert p2p_chart.__all__ == ["show_profile_chart"]

    def test_fresnel_60pct_factor_import(self):
        from NoWires.constants import FRESNEL_60PCT_FACTOR
        assert 0.0 < FRESNEL_60PCT_FACTOR < 1.0