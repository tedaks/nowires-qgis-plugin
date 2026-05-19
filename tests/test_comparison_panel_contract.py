# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Contract tests for comparison_panel module.

comparison_panel.py depends on QGIS processing context, so we test
structural invariants and pure-data helpers only.
"""


class TestComparisonPanelContract:
    def test_module_imports(self):
        import comparison.panel as comparison_panel
        assert hasattr(comparison_panel, "run_panel_coverage")

    def test_all_declared_exports(self):
        import comparison.panel as comparison_panel
        assert "run_panel_coverage" in comparison_panel.__all__