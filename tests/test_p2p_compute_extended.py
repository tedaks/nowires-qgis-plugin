# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended tests for p2p_compute.py — NaN elevation handling and DEM error paths."""

import importlib.util
import os
import sys
import types
from types import SimpleNamespace

import pytest

from NoWires.p2p.analysis_params import P2PAnalysisParams
from NoWires.radio import ITMResult


_STOMPED_MODULES = ("NoWires.dem_downloader", "NoWires.p2p.params",
                    "NoWires.processing_utils", "NoWires._test_p2p_compute")


@pytest.fixture(autouse=True)
def _restore_stomped_modules():
    saved = {k: sys.modules.get(k) for k in _STOMPED_MODULES}
    yield
    for k in _STOMPED_MODULES:
        if k in sys.modules and sys.modules[k] is not saved.get(k):
            if saved.get(k) is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = saved.get(k)


class _Feedback:
    def __init__(self):
        self.messages = []
    def pushInfo(self, m):
        self.messages.append(m)
    def setProgress(self, _):
        pass


def _make_params():
    return P2PAnalysisParams(
        tx_lat=14.0, tx_lon=121.0, rx_lat=14.001, rx_lon=121.001,
        tx_h=30.0, rx_h=10.0, f_mhz=900.0,
        polarization=1, climate=1,
        time_pct=50.0, location_pct=50.0, situation_pct=50.0,
        tx_power=30.0, tx_gain=10.0, rx_gain=8.0,
        cable_loss=1.0, rx_sens=-90.0,
        k_factor=4.0 / 3.0, n0=301.0, epsilon=15.0, sigma=0.005,
        tx_antenna_config=SimpleNamespace(preset="omni"),
        rx_antenna_config=SimpleNamespace(preset="omni"),
        clutter_enabled=False,
        profile_dest="/tmp/profile.gpkg",
        fresnel_dest="/tmp/fresnel.gpkg",
        markers_dest="/tmp/markers.gpkg",
        show_chart=False,
        context=object(),
        feedback=_Feedback(),
        output_profile="OUTPUT_PROFILE",
        output_fresnel="OUTPUT_FRESNEL",
        output_markers="OUTPUT_MARKERS",
        output_report_csv="", output_report_json="", output_report_html="",
    )


def _load_p2p_compute(monkeypatch):
    qgis_core = sys.modules.setdefault("qgis.core", types.ModuleType("qgis.core"))
    if not hasattr(qgis_core, "QgsProcessingException"):
        monkeypatch.setattr(qgis_core, "QgsProcessingException", RuntimeError, raising=False)

    for name in ("NoWires.dem_downloader", "NoWires.p2p.params",
                 "NoWires.processing_utils"):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))

    monkeypatch.setattr(sys.modules["NoWires.dem_downloader"],
                        "ensure_dem_for_area", lambda *a, **kw: "/tmp/dem.tif", raising=False)
    monkeypatch.setattr(sys.modules["NoWires.dem_downloader"],
                        "get_temp_dir", lambda: "/tmp/nowires_test", raising=False)
    monkeypatch.setattr(sys.modules["NoWires.p2p.params"],
                        "report_p2p_results", lambda *a, **kw: None, raising=False)
    monkeypatch.setattr(sys.modules["NoWires.processing_utils"],
                        "queue_layer_for_loading", lambda *a, **kw: None, raising=False)
    monkeypatch.setattr(sys.modules["NoWires.processing_utils"],
                        "register_destination_layer", lambda *a, **kw: None, raising=False)

    module_path = os.path.join(os.path.dirname(__file__), "..", "p2p/compute.py")
    spec = importlib.util.spec_from_file_location("NoWires._test_p2p_compute", module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["NoWires._test_p2p_compute"] = mod
    spec.loader.exec_module(mod)
    return mod


def _stub_outputs_and_layers(p2p_compute, monkeypatch):
    monkeypatch.setattr(p2p_compute, "_write_p2p_output_layers",
        lambda *a, **kw: ("/tmp/p.gpkg", "/tmp/f.gpkg", "/tmp/fl.gpkg", "/tmp/m.gpkg"))
    monkeypatch.setattr(p2p_compute, "_load_p2p_qgis_layers", lambda *a, **kw: None)
    monkeypatch.setattr(p2p_compute, "_write_p2p_reports", lambda *a, **kw: None)
    monkeypatch.setattr(p2p_compute, "antenna_gain_adjustment_db", lambda *a, **kw: 0.0)


class TestP2PNANElevationHandling:
    def test_all_nan_elevations_raises_exception(self, monkeypatch):
        p2p_compute = _load_p2p_compute(monkeypatch)

        class _AllNANGrid:
            def __init__(self, _path):
                pass
            def __enter__(self):
                return self
            def __exit__(self, _et, _ev, _tb):
                return False
            def terrain_profile(self, *_a, **_kw):
                return [(0.0, float("nan")), (1000.0, float("nan"))]

        monkeypatch.setattr(p2p_compute, "ElevationGrid", _AllNANGrid)
        monkeypatch.setattr(p2p_compute, "itm_p2p_loss",
            lambda **_kw: ITMResult(loss_db=110.0, mode=1, warnings=0))

        with pytest.raises(Exception, match="NaN"):
            p2p_compute.run_p2p_analysis(_make_params())

    def test_partial_nan_interpolates_and_continues(self, monkeypatch):
        p2p_compute = _load_p2p_compute(monkeypatch)
        _stub_outputs_and_layers(p2p_compute, monkeypatch)

        class _PartialNANGrid:
            def __init__(self, _path):
                pass
            def __enter__(self):
                return self
            def __exit__(self, _et, _ev, _tb):
                return False
            def terrain_profile(self, *_a, **_kw):
                return [(0.0, 10.0), (500.0, float("nan")), (1000.0, 12.0)]

        monkeypatch.setattr(p2p_compute, "ElevationGrid", _PartialNANGrid)
        monkeypatch.setattr(p2p_compute, "itm_p2p_loss",
            lambda **_kw: ITMResult(loss_db=110.0, mode=1, warnings=0))

        result = p2p_compute.run_p2p_analysis(_make_params())
        assert result["OUTPUT_PROFILE"] == "/tmp/p.gpkg"

    def test_single_nan_elevation_interpolates(self, monkeypatch):
        p2p_compute = _load_p2p_compute(monkeypatch)
        _stub_outputs_and_layers(p2p_compute, monkeypatch)

        class _SingleNANGrid:
            def __init__(self, _path):
                pass
            def __enter__(self):
                return self
            def __exit__(self, _et, _ev, _tb):
                return False
            def terrain_profile(self, *_a, **_kw):
                return [(0.0, 10.0), (1000.0, float("nan"))]

        monkeypatch.setattr(p2p_compute, "ElevationGrid", _SingleNANGrid)
        monkeypatch.setattr(p2p_compute, "itm_p2p_loss",
            lambda **_kw: ITMResult(loss_db=110.0, mode=1, warnings=0))

        result = p2p_compute.run_p2p_analysis(_make_params())
        assert result["OUTPUT_PROFILE"] == "/tmp/p.gpkg"


class TestP2PDEMFailure:
    def test_dem_download_returns_none_raises(self, monkeypatch):
        p2p_compute = _load_p2p_compute(monkeypatch)
        monkeypatch.setattr(p2p_compute,
            "ensure_dem_for_area", lambda *a, **kw: None)

        with pytest.raises(Exception, match="Failed to obtain DEM"):
            p2p_compute.run_p2p_analysis(_make_params())

    def test_terrain_profile_too_short_raises(self, monkeypatch):
        p2p_compute = _load_p2p_compute(monkeypatch)

        class _ShortProfileGrid:
            def __init__(self, _path):
                pass
            def __enter__(self):
                return self
            def __exit__(self, _et, _ev, _tb):
                return False
            def terrain_profile(self, *_a, **_kw):
                return [(0.0, 10.0)]

        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ShortProfileGrid)

        with pytest.raises(Exception, match="too short"):
            p2p_compute.run_p2p_analysis(_make_params())


class TestP2PFresnelAnalysis:
    def test_los_blocked_flag(self, monkeypatch):
        p2p_compute = _load_p2p_compute(monkeypatch)
        _stub_outputs_and_layers(p2p_compute, monkeypatch)
        captured_payload = {}

        class _Grid:
            def __init__(self, _path):
                pass
            def __enter__(self):
                return self
            def __exit__(self, _et, _ev, _tb):
                return False
            def terrain_profile(self, *_a, **_kw):
                return [(0.0, 10.0), (1000.0, 12.0)]

        monkeypatch.setattr(p2p_compute, "ElevationGrid", _Grid)
        monkeypatch.setattr(p2p_compute, "itm_p2p_loss",
            lambda **_kw: ITMResult(loss_db=110.0, mode=1, warnings=0))

        def _capture_payload(*a, **kw):
            captured_payload.update(kw)
            return {"results": {"itm_loss_db": 110.0, "free_space_loss_db": 100.0,
                "total_path_loss_db": 110.0, "eirp_dbm": 37.0, "clutter_tx_db": 0.0,
                "clutter_rx_db": 0.0, "received_power_dbm": -63.0, "link_margin_db": 27.0,
                "propagation_mode_name": "Line-of-Sight", "antenna_gain_adjustment_db": 0.0,
                "fade_margin_class": "good", "reliability_summary": "OK",
                "availability_method": "n/a", "availability_estimate_pct": None,
                "fresnel_1_violated": False, "fresnel_60_violated": False,
                "max_fresnel_radius_m": 10.0, "tx_cch_m": 0.0, "rx_cch_m": 0.0,
                "clutter_method": "", "clutter_percentile": 50.0, "bel_rx_db": 0.0},
                "inputs": {}, "status": {}}

        monkeypatch.setattr(p2p_compute, "build_p2p_report_payload", _capture_payload)

        p2p_compute.run_p2p_analysis(_make_params())
        assert "los_blocked" in captured_payload
