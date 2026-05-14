# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Contract tests for p2p_chart module.

p2p_chart.py depends heavily on matplotlib and QGIS Qt, so we test
import-level invariants and the pure data-preparation parts only.
"""



class TestP2pChartModuleContract:
    def test_module_imports(self):
        import p2p_chart
        assert hasattr(p2p_chart, "show_profile_chart")
        assert hasattr(p2p_chart, "_add_obstruction_annotations")
        assert hasattr(p2p_chart, "_setup_tooltip")

    def test_all_declared_exports(self):
        import p2p_chart
        assert p2p_chart.__all__ == ["show_profile_chart"]

    def test_fresnel_60pct_factor_import(self):
        from defaults import FRESNEL_60PCT_FACTOR
        assert 0.0 < FRESNEL_60PCT_FACTOR < 1.0