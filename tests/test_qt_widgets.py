# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for matplotlib chart, legend, and antenna preview widgets."""

import numpy as np
import pytest

pytestmark = pytest.mark.qgis_integration


@pytest.fixture(autouse=True)
def _setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")


class TestP2PChart:
    def test_show_profile_chart_basic(self, qgis_app, monkeypatch):
        from NoWires.p2p.chart import show_profile_chart
        from unittest.mock import MagicMock
        from qgis.PyQt.QtWidgets import QMainWindow

        main_win = QMainWindow()
        mock_iface = MagicMock()
        mock_iface.mainWindow.return_value = main_win
        monkeypatch.setattr("qgis.utils.iface", mock_iface, raising=False)

        n = 100
        distances = np.linspace(0, 5000, n)
        elevations = np.full(n, 100.0)
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 15.0)

        mock_result = MagicMock()
        mock_result.mode = 0
        mock_result.loss_db = 110.0
        mock_result.warnings = 0

        try:
            show_profile_chart(
                distances=distances, elevations=elevations,
                terrain_bulge=terrain, los_h=los_h, fresnel_r=fresnel_r,
                dist_m=5000.0, tx_h=30.0, rx_h=10.0, f_mhz=900.0,
                result=mock_result, k_factor=1.333,
                tx_power=30.0, tx_gain=10.0, rx_gain=5.0,
                cable_loss=1.0, rx_sens=-90.0,
                prx_dbm=-70.0, margin_db=20.0, itm_loss_db=110.0,
            )
        except Exception as e:
            pytest.fail(f"show_profile_chart raised: {e}")

    def test_show_profile_chart_headless_no_iface(self, qgis_app, monkeypatch):
        from NoWires.p2p.chart import show_profile_chart
        from unittest.mock import MagicMock

        if "qgis.utils" in __import__("sys").modules:
            monkeypatch.delattr("qgis.utils", "iface", raising=False)

        n = 10
        distances = np.linspace(0, 1000, n)
        elevations = np.full(n, 100.0)
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 10.0)

        mock_result = MagicMock()
        mock_result.mode = 0
        mock_result.loss_db = 110.0
        mock_result.warnings = 0

        show_profile_chart(
            distances=distances, elevations=elevations,
            terrain_bulge=terrain, los_h=los_h, fresnel_r=fresnel_r,
            dist_m=1000.0, tx_h=30.0, rx_h=10.0, f_mhz=900.0,
            result=mock_result, k_factor=1.333,
            tx_power=30.0, tx_gain=10.0, rx_gain=5.0,
            cable_loss=1.0, rx_sens=-90.0,
        )


class TestChartHelpers:
    def test_nan_safe_fmt_normal(self):
        from NoWires.p2p.chart_helpers import _nan_safe_fmt
        assert _nan_safe_fmt(123.456, ".2f") == "123.46"

    def test_nan_safe_fmt_nan(self):
        from NoWires.p2p.chart_helpers import _nan_safe_fmt
        assert _nan_safe_fmt(float("nan"), ".2f") == ""

    def test_nan_safe_fmt_inf(self):
        from NoWires.p2p.chart_helpers import _nan_safe_fmt
        result = _nan_safe_fmt(float("inf"), ".2f")
        assert result != ""

    def test_add_obstruction_annotations_no_obstructions(self, qgis_app):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from NoWires.p2p.chart_helpers import add_obstruction_annotations

        fig, ax = plt.subplots()
        n = 10
        d_km = np.linspace(0, 5, n)
        terrain = np.full(n, 100.0)
        los_h = np.full(n, 120.0)
        fresnel_r = np.full(n, 10.0)

        annotations = add_obstruction_annotations(ax, d_km, terrain, los_h, fresnel_r)
        assert isinstance(annotations, list)
        plt.close(fig)


class TestCoverageLegend:
    def test_legend_widget_creation(self, qgis_app):
        from qgis.PyQt.QtWidgets import QWidget
        from NoWires.radio_coverage.legend import CoverageLegendWidget

        parent = QWidget()
        try:
            canvas = QWidget(parent)
            widget = CoverageLegendWidget(canvas, -90.0)
            assert widget is not None
            widget.deleteLater()
        finally:
            parent.deleteLater()

    def test_show_coverage_legend(self, qgis_app):
        from qgis.PyQt.QtWidgets import QWidget
        from NoWires.radio_coverage.legend import show_coverage_legend

        parent = QWidget()
        widget = show_coverage_legend(-90.0)
        if widget is not None:
            widget.deleteLater()
        parent.deleteLater()


class TestAntennaPatternPreview:
    def test_normalize_to_max_basic(self):
        from NoWires.antenna_pattern_preview import _normalize_to_max
        points = [(0.0, 5.0), (90.0, 10.0), (180.0, 2.0)]
        result = _normalize_to_max(points)
        assert len(result) == 3
        assert result[1][1] == 0.0  # peak is 10.0, 10-10=0

    def test_normalize_to_max_empty(self):
        from NoWires.antenna_pattern_preview import _normalize_to_max
        assert _normalize_to_max([]) == []

    def test_polar_plot_widget(self, qgis_app):
        from NoWires.antenna_pattern_preview import _PolarPlot
        widget = _PolarPlot()
        assert widget.minimumWidth() == 400
        points = [(0.0, 0.0), (45.0, -3.0), (90.0, -10.0),
                  (135.0, -3.0), (180.0, 0.0)]
        widget.set_points(points)
        assert len(widget._points) == 5
        widget.deleteLater()

    def test_antenna_preview_dialog(self, qgis_app, tmp_path):
        from NoWires.antenna_pattern_preview import AntennaPatternPreviewDialog

        csv_path = tmp_path / "pattern.csv"
        csv_path.write_text("angle_deg,gain_db\n0,0\n45,-3\n90,-10\n135,-3\n180,0\n225,-3\n270,-10\n315,-3\n360,0\n")

        dlg = AntennaPatternPreviewDialog()
        assert dlg is not None
        dlg.deleteLater()
