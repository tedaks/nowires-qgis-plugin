# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import builtins
import sys
from unittest import mock

import numpy as np
import pytest

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False
    plt = None

from NoWires.p2p.chart_helpers import (
    add_obstruction_annotations,
    make_export_csv,
    make_save_png,  # noqa: F401  — tested via png save callback
    setup_tooltip,  # noqa: F401  — tested via mpl event connection
)
from NoWires.p2p.chart_format import build_chart_status_text, build_obstruction_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_axes():
    fig = plt.Figure(figsize=(6, 4))
    ax = fig.add_subplot(111)
    return ax


_skip_no_mpl = pytest.mark.skipif(not _HAS_MPL, reason="matplotlib not available")


def _install_qgis_mocks(qt_widgets_overrides=None):
    m_qt = mock.MagicMock()
    if qt_widgets_overrides:
        for attr, val in qt_widgets_overrides.items():
            setattr(m_qt, attr, val)
    m_pyqt = mock.MagicMock()
    m_pyqt.QtWidgets = m_qt
    m_qgis = mock.MagicMock()
    m_qgis.PyQt = m_pyqt
    return mock.patch.dict("sys.modules", {
        "qgis": m_qgis,
        "qgis.PyQt": m_pyqt,
        "qgis.PyQt.QtWidgets": m_qt,
    })


# ---------------------------------------------------------------------------
# add_obstruction_annotations
# ---------------------------------------------------------------------------


@_skip_no_mpl
def test_add_obstruction_annotations_empty_path():
    ax = _make_axes()
    empty = np.array([], dtype=np.float64)
    result = add_obstruction_annotations(ax, empty, empty, empty, empty)
    assert result == []
    plt.close("all")


@_skip_no_mpl
def test_add_obstruction_annotations_no_obstruction():
    ax = _make_axes()
    d_km = np.array([0.0, 1.0, 2.0], dtype=np.float64)
    terrain = np.array([10.0, 10.0, 10.0], dtype=np.float64)
    los = np.array([50.0, 50.0, 50.0], dtype=np.float64)
    fresnel = np.array([5.0, 5.0, 5.0], dtype=np.float64)
    result = add_obstruction_annotations(ax, d_km, terrain, los, fresnel)
    assert result == []
    plt.close("all")


@_skip_no_mpl
def test_add_obstruction_annotations_with_obstruction():
    ax = _make_axes()
    d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    terrain = np.array([10.0, 10.0, 60.0, 10.0, 10.0], dtype=np.float64)
    los = np.array([50.0, 50.0, 50.0, 50.0, 50.0], dtype=np.float64)
    fresnel = np.array([5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float64)
    result = add_obstruction_annotations(ax, d_km, terrain, los, fresnel)
    assert len(result) == 1
    assert isinstance(result[0], matplotlib.text.Annotation)
    plt.close("all")


# ---------------------------------------------------------------------------
# make_export_csv
# ---------------------------------------------------------------------------


def test_make_export_csv_with_nan_values(tmp_path):
    path = str(tmp_path / "test_nan.csv")

    distances = np.array([0.0, 1000.0, 2000.0], dtype=np.float64)
    terrain_bulge = np.array([10.0, float("nan"), 10.0], dtype=np.float64)
    los_h = np.array([50.0, 50.0, float("nan")], dtype=np.float64)
    fresnel_r = np.array([5.0, float("nan"), float("nan")], dtype=np.float64)

    qfiledialog = mock.MagicMock()
    qfiledialog.getSaveFileName.return_value = (path, "CSV Files (*.csv)")
    with _install_qgis_mocks({"QFileDialog": qfiledialog}):
        export_fn = make_export_csv(
            distances, terrain_bulge, los_h, fresnel_r, 900.0, 2000.0, None)
        export_fn()

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    assert len(lines) == 4

    row0 = lines[1].split(",")
    assert row0[1] == "10.00"
    assert row0[2] == "50.00"

    assert ",," in lines[2]

    row2 = lines[3].split(",")
    assert row2[2] == ""


def test_make_export_csv_header_and_format(tmp_path):
    path = str(tmp_path / "test_header.csv")

    distances = np.array([0.0, 1000.0], dtype=np.float64)
    terrain_bulge = np.array([10.0, 20.0], dtype=np.float64)
    los_h = np.array([50.0, 50.0], dtype=np.float64)
    fresnel_r = np.array([3.0, 4.0], dtype=np.float64)

    qfiledialog = mock.MagicMock()
    qfiledialog.getSaveFileName.return_value = (path, "CSV Files (*.csv)")
    with _install_qgis_mocks({"QFileDialog": qfiledialog}):
        export_fn = make_export_csv(
            distances, terrain_bulge, los_h, fresnel_r, 900.0, 1000.0, None)
        export_fn()

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    header = lines[0]
    assert "distance_m" in header
    assert "terrain_elevation_m" in header
    assert "los_m" in header
    assert "fresnel_radius_m" in header
    assert "clearance_m" in header
    assert "obstructs_los" in header

    row0 = lines[1].split(",")
    assert row0[0] == "0.00"
    assert row0[1] == "10.00"
    assert row0[5] == "0"


# ---------------------------------------------------------------------------
# show_profile_chart – import error guard
# ---------------------------------------------------------------------------


def test_show_profile_chart_with_import_error_returns_none():
    save = sys.modules.get("qgis.utils")
    mock_qgis = mock.MagicMock()
    mock_qgis.iface = mock.MagicMock()
    sys.modules["qgis.utils"] = mock_qgis

    mpl_keys = [k for k in list(sys.modules) if k.startswith("matplotlib")]
    mpl_backup = {k: sys.modules[k] for k in mpl_keys}
    for k in mpl_keys:
        del sys.modules[k]

    _original_import = builtins.__import__

    def _block(name, *args, **kwargs):
        if name.startswith("matplotlib") or name == "matplotlib":
            raise ImportError("Blocked for test: {}".format(name))
        return _original_import(name, *args, **kwargs)

    try:
        builtins.__import__ = _block
        from NoWires.p2p.chart import show_profile_chart

        result = show_profile_chart(
            distances=np.array([0, 1000], dtype=np.float64),
            elevations=np.array([10, 10], dtype=np.float64),
            terrain_bulge=np.array([10, 10], dtype=np.float64),
            los_h=np.array([20, 20], dtype=np.float64),
            fresnel_r=np.array([1, 1], dtype=np.float64),
            dist_m=1000,
            tx_h=20, rx_h=20,
            f_mhz=900,
            result="LOS", k_factor=1.33,
            tx_power=30, tx_gain=10, rx_gain=10,
            cable_loss=2, rx_sens=-100,
        )
        assert result is None
    finally:
        builtins.__import__ = _original_import
        sys.modules.update(mpl_backup)
        if save is not None:
            sys.modules["qgis.utils"] = save
        else:
            sys.modules.pop("qgis.utils", None)


# ---------------------------------------------------------------------------
# build_chart_status_text  (chart_format.py)
# ---------------------------------------------------------------------------

_Result = mock.MagicMock


def test_build_chart_status_text_viable():
    r = _Result()
    r.loss_db = 120.0
    text = build_chart_status_text(r, prx_dbm=-50.0, margin_db=10.0)
    assert "VIABLE" in text
    assert "120.0 dB" in text
    assert "-50.0 dBm" in text
    assert "10.0 dB" in text


def test_build_chart_status_text_not_viable():
    r = _Result()
    r.loss_db = 120.0
    text = build_chart_status_text(r, prx_dbm=-70.0, margin_db=-5.0)
    assert "NOT VIABLE" in text


def test_build_chart_status_text_zero_margin():
    r = _Result()
    r.loss_db = 120.0
    text = build_chart_status_text(r, prx_dbm=-50.0, margin_db=0.0)
    assert "VIABLE" in text


def test_build_chart_status_text_no_margin():
    r = _Result()
    r.loss_db = 120.0
    text = build_chart_status_text(r, prx_dbm=-50.0, margin_db=None)
    assert "VIABLE" not in text
    assert "NOT VIABLE" not in text
    assert "Margin" not in text
    assert "-50.0 dBm" in text
    assert "120.0 dB" in text


def test_build_chart_status_text_with_itm_loss_db():
    r = _Result()
    r.loss_db = 9999.0
    text = build_chart_status_text(
        r, prx_dbm=-50.0, margin_db=10.0, itm_loss_db=110.0)
    assert "110.0 dB" in text
    assert "9999.0" not in text


def test_build_chart_status_text_no_itm_loss_uses_result():
    r = _Result()
    r.loss_db = 135.0
    text = build_chart_status_text(r, prx_dbm=-40.0, margin_db=5.0, itm_loss_db=None)
    assert "135.0 dB" in text


def test_build_obstruction_data_no_obstructions():
    d_km = np.array([0.0, 1.0, 2.0], dtype=np.float64)
    terrain = np.array([10.0, 10.0, 10.0], dtype=np.float64)
    los = np.array([50.0, 50.0, 50.0], dtype=np.float64)
    fresnel = np.array([5.0, 5.0, 5.0], dtype=np.float64)
    result = build_obstruction_data(d_km, terrain, los, fresnel)
    assert result == []


def test_build_obstruction_data_single_peak():
    d_km = np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    terrain = np.array([10.0, 10.0, 60.0, 10.0, 10.0], dtype=np.float64)
    los = np.array([50.0, 50.0, 50.0, 50.0, 50.0], dtype=np.float64)
    fresnel = np.array([5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float64)
    result = build_obstruction_data(d_km, terrain, los, fresnel)
    assert len(result) == 1
    idx, x, y, los_val, fr, deficit = result[0]
    assert idx == 2
    assert x == pytest.approx(2.0)
    assert y == pytest.approx(60.0)
    assert deficit == pytest.approx(15.0)


def test_build_obstruction_data_defens_zero_when_below_fresnel():
    d_km = np.array([0.0, 1.0], dtype=np.float64)
    terrain = np.array([40.0, 40.0], dtype=np.float64)
    los = np.array([50.0, 50.0], dtype=np.float64)
    fresnel = np.array([5.0, 5.0], dtype=np.float64)
    result = build_obstruction_data(d_km, terrain, los, fresnel)
    assert result == []
