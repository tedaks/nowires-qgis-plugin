# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for p2p_compute: NaN handling and FSPL edge cases.

Tests import and verify the actual plugin modules (nan_utils, itm.propagation)
rather than reimplementing their logic inline.
"""

import os
import math
import importlib.util
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from NoWires.p2p_analysis_params import P2PAnalysisParams
from NoWires.radio import ITMResult
from NoWires.constants import ITM_LOSS_UPPER_BOUND
from nan_utils import interpolate_nan_elevations, interpolate_nan_array
from itm.propagation import free_space_loss


class TestNaNInterpolation:
    """Verify that NaN elevation values are interpolated, not zeroed."""

    def test_interpolate_nan_elevations_replaces_nan_with_interpolated(self):
        elevations = [0.0, float("nan"), 100.0]
        result = interpolate_nan_elevations(elevations)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(50.0)
        assert result[2] == pytest.approx(100.0)

    def test_interpolate_nan_elevations_all_nan_returns_unchanged(self):
        elevations = [float("nan"), float("nan")]
        result = interpolate_nan_elevations(elevations)
        assert len(result) == 2
        assert all(math.isnan(v) for v in result)

    def test_interpolate_nan_elevations_no_nan_unchanged(self):
        elevations = [10.0, 20.0, 30.0]
        result = interpolate_nan_elevations(elevations)
        assert result == pytest.approx([10.0, 20.0, 30.0])

    def test_interpolate_nan_elevations_edge_nan_uses_nearest(self):
        elevations = [float("nan"), 20.0, 30.0]
        result = interpolate_nan_elevations(elevations)
        assert result[0] == pytest.approx(20.0)

    def test_interpolate_nan_elevations_trailing_nan_uses_nearest(self):
        elevations = [10.0, 20.0, float("nan")]
        result = interpolate_nan_elevations(elevations)
        assert result[2] == pytest.approx(20.0)

    def test_interpolate_nan_array_returns_ndarray(self):
        arr = np.array([1.0, np.nan, 3.0])
        result = interpolate_nan_array(arr)
        assert isinstance(result, np.ndarray)
        assert result[1] == pytest.approx(2.0)

    def test_interpolate_nan_array_preserves_valid(self):
        arr = np.array([10.0, 20.0, 30.0])
        result = interpolate_nan_array(arr)
        np.testing.assert_array_almost_equal(result, arr)


class TestFSPLFromModule:
    """Verify FSPL computation using the actual ITM propagation module."""

    def test_fspl_positive_distance_and_frequency(self):
        result = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        assert result > 0

    def test_fspl_zero_distance_raises_value_error(self):
        with pytest.raises(ValueError):
            free_space_loss(d__meter=0.0, f__mhz=900.0)

    def test_fspl_zero_frequency_raises_value_error(self):
        with pytest.raises(ValueError):
            free_space_loss(d__meter=1000.0, f__mhz=0.0)

    def test_fspl_uses_correct_constant(self):
        expected = 32.45 + 20.0 * math.log10(900.0) + 20.0 * math.log10(1.0)
        result = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        assert result == pytest.approx(expected, rel=1e-10)

    def test_fspl_increases_with_distance(self):
        fspl_1km = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        fspl_10km = free_space_loss(d__meter=10000.0, f__mhz=900.0)
        assert fspl_10km > fspl_1km

    def test_fspl_increases_with_frequency(self):
        fspl_900 = free_space_loss(d__meter=1000.0, f__mhz=900.0)
        fspl_2400 = free_space_loss(d__meter=1000.0, f__mhz=2400.0)
        assert fspl_2400 > fspl_900


class _Feedback:
    def pushInfo(self, _message):
        pass

    def setProgress(self, _value):
        pass


class _ElevationGrid:
    def __init__(self, _path):
        pass

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        return False

    def terrain_profile(self, *_args, **_kwargs):
        return [(0.0, 10.0), (1000.0, 12.0)]


class _ClutterGrid:
    source = "auto"

    def __init__(self):
        self.closed = False

    def sample_category(self, _lat, _lon):
        return "open"

    def close(self):
        self.closed = True


def _make_p2p_params():
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
        clutter_enabled=True,
        profile_dest="/tmp/profile.gpkg",
        fresnel_dest="/tmp/fresnel.gpkg",
        markers_dest="/tmp/markers.gpkg",
        show_chart=False,
        context=object(),
        feedback=_Feedback(),
        output_profile="OUTPUT_PROFILE",
        output_fresnel="OUTPUT_FRESNEL",
        output_markers="OUTPUT_MARKERS",
        output_report_csv="OUTPUT_REPORT_CSV",
        output_report_json="OUTPUT_REPORT_JSON",
        output_report_html="OUTPUT_REPORT_HTML",
    )


def _load_p2p_compute_with_test_stubs(monkeypatch):
    qgis_core = sys.modules.get("qgis.core")
    if qgis_core is None:
        qgis_core = types.ModuleType("qgis.core")
        monkeypatch.setitem(sys.modules, "qgis.core", qgis_core)
    if not hasattr(qgis_core, "QgsProcessingException"):
        qgis_core.QgsProcessingException = RuntimeError
    dem_stub = types.ModuleType("NoWires.dem_downloader")
    dem_stub.ensure_dem_for_area = lambda *args, **kwargs: "/tmp/dem.tif"
    p2p_params_stub = types.ModuleType("NoWires.p2p_params")
    p2p_params_stub.report_p2p_results = lambda *args, **kwargs: None
    processing_utils_stub = types.ModuleType("NoWires.processing_utils")
    processing_utils_stub.queue_layer_for_loading = lambda *args, **kwargs: None
    processing_utils_stub.register_destination_layer = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "NoWires.dem_downloader", dem_stub)
    monkeypatch.setitem(sys.modules, "NoWires.p2p_params", p2p_params_stub)
    monkeypatch.setitem(sys.modules, "NoWires.processing_utils", processing_utils_stub)
    module_name = "NoWires._test_p2p_compute"
    module_path = os.path.join(os.path.dirname(__file__), "..", "p2p_compute.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    p2p_compute = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, p2p_compute)
    spec.loader.exec_module(p2p_compute)
    return p2p_compute


def test_run_p2p_analysis_closes_auto_clutter_grid(monkeypatch):
    p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)

    auto_grid = _ClutterGrid()
    monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
    monkeypatch.setattr(
        p2p_compute,
        "ensure_clutter_grid_for_area",
        lambda *args, **kwargs: auto_grid,
    )
    monkeypatch.setattr(
        p2p_compute,
        "itm_p2p_loss",
        lambda **_kwargs: ITMResult(loss_db=110.0, mode=1, warnings=0),
    )
    monkeypatch.setattr(p2p_compute, "antenna_gain_adjustment_db", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(
        p2p_compute,
        "_write_p2p_output_layers",
        lambda *args, **kwargs: ("/tmp/profile.gpkg", "/tmp/fresnel.gpkg", "/tmp/markers.gpkg"),
    )
    monkeypatch.setattr(p2p_compute, "_load_p2p_qgis_layers", lambda *args, **kwargs: None)

    result = p2p_compute.run_p2p_analysis(_make_p2p_params())

    assert result["OUTPUT_PROFILE"] == "/tmp/profile.gpkg"
    assert auto_grid.closed


def test_run_p2p_analysis_leaves_supplied_clutter_grid_open(monkeypatch):
    p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)

    supplied_grid = _ClutterGrid()
    params = _make_p2p_params()
    params.clutter_grid = supplied_grid
    monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
    monkeypatch.setattr(
        p2p_compute,
        "ensure_clutter_grid_for_area",
        lambda *args, **kwargs: pytest.fail("should not auto-load clutter"),
    )
    monkeypatch.setattr(
        p2p_compute,
        "itm_p2p_loss",
        lambda **_kwargs: ITMResult(loss_db=110.0, mode=1, warnings=0),
    )
    monkeypatch.setattr(p2p_compute, "antenna_gain_adjustment_db", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(
        p2p_compute,
        "_write_p2p_output_layers",
        lambda *args, **kwargs: ("/tmp/profile.gpkg", "/tmp/fresnel.gpkg", "/tmp/markers.gpkg"),
    )
    monkeypatch.setattr(p2p_compute, "_load_p2p_qgis_layers", lambda *args, **kwargs: None)

    p2p_compute.run_p2p_analysis(params)

    assert not supplied_grid.closed


class TestP2PClutterGridCloseErrorIsolation:
    """Verify that errors closing a supplied clutter_grid are silently caught."""

    class _FailingCloseGrid:
        source = "auto"
        closed = False

        def sample_category(self, _lat, _lon):
            return "open"

        def close(self):
            self.closed = True
            raise RuntimeError("close failed")


class TestP2PMinDistanceValidation:
    """Verify that P2P analysis rejects paths shorter than _MIN_P2P_DISTANCE_M."""

    def test_zero_distance_raises_processing_exception(self, monkeypatch):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = P2PAnalysisParams(
            tx_lat=14.0, tx_lon=121.0, rx_lat=14.0, rx_lon=121.0,
            tx_h=30.0, rx_h=10.0, f_mhz=900.0,
            polarization=1, climate=1,
            time_pct=50.0, location_pct=50.0, situation_pct=50.0,
            tx_power=30.0, tx_gain=10.0, rx_gain=8.0,
            cable_loss=1.0, rx_sens=-90.0,
            k_factor=4.0 / 3.0, n0=301.0, epsilon=15.0, sigma=0.005,
            tx_antenna_config=SimpleNamespace(preset="omni"),
            rx_antenna_config=SimpleNamespace(preset="omni"),
            clutter_enabled=False,
            context=object(),
            feedback=_Feedback(),
            output_profile="OUTPUT_PROFILE",
            output_fresnel="OUTPUT_FRESNEL",
            output_markers="OUTPUT_MARKERS",
            output_report_csv="", output_report_json="", output_report_html="",
        )
        with pytest.raises(Exception, match="too close"):
            p2p_compute.run_p2p_analysis(params)


class TestP2PITMLossCap:
    """Verify that P2P analysis caps ITM loss at ITM_LOSS_UPPER_BOUND."""

    def test_loss_capped_at_upper_bound(self, monkeypatch):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = _make_p2p_params()
        params.clutter_enabled = False
        params.clutter_grid = None
        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
        monkeypatch.setattr(
            p2p_compute,
            "itm_p2p_loss",
            lambda **_kwargs: ITMResult(loss_db=999.0, mode=2, warnings=0),
        )
        monkeypatch.setattr(p2p_compute, "antenna_gain_adjustment_db", lambda *a, **kw: 0.0)
        monkeypatch.setattr(
            p2p_compute,
            "_write_p2p_output_layers",
            lambda *a, **kw: ("/tmp/profile.gpkg", "/tmp/fresnel.gpkg", "/tmp/markers.gpkg"),
        )
        monkeypatch.setattr(p2p_compute, "_load_p2p_qgis_layers", lambda *a, **kw: None)
        monkeypatch.setattr(p2p_compute, "_write_p2p_reports", lambda *a, **kw: None)
        monkeypatch.setattr(p2p_compute, "report_p2p_results", lambda *a, **kw: None)

        captured = {}
        def _capturing_build_payload(*args, **kwargs):
            captured.update(kwargs)
            return {"results": {}, "inputs": {}, "status": {}}
        monkeypatch.setattr(p2p_compute, "build_p2p_report_payload", _capturing_build_payload)
        p2p_compute.run_p2p_analysis(params)
        assert captured["itm_loss_db"] == ITM_LOSS_UPPER_BOUND

    def test_loss_not_capped_below_upper_bound(self, monkeypatch):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = _make_p2p_params()
        params.clutter_enabled = False
        params.clutter_grid = None
        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
        monkeypatch.setattr(
            p2p_compute,
            "itm_p2p_loss",
            lambda **_kwargs: ITMResult(loss_db=150.0, mode=1, warnings=0),
        )
        monkeypatch.setattr(p2p_compute, "antenna_gain_adjustment_db", lambda *a, **kw: 0.0)
        monkeypatch.setattr(
            p2p_compute,
            "_write_p2p_output_layers",
            lambda *a, **kw: ("/tmp/profile.gpkg", "/tmp/fresnel.gpkg", "/tmp/markers.gpkg"),
        )
        monkeypatch.setattr(p2p_compute, "_load_p2p_qgis_layers", lambda *a, **kw: None)
        monkeypatch.setattr(p2p_compute, "_write_p2p_reports", lambda *a, **kw: None)
        monkeypatch.setattr(p2p_compute, "report_p2p_results", lambda *a, **kw: None)

        captured = {}
        def _capturing_build_payload(*args, **kwargs):
            captured.update(kwargs)
            return {"results": {}, "inputs": {}, "status": {}}
        monkeypatch.setattr(p2p_compute, "build_p2p_report_payload", _capturing_build_payload)
        p2p_compute.run_p2p_analysis(params)
        assert captured["itm_loss_db"] == 150.0


class TestP2PITMFailureRejection:
    """Verify that P2P analysis rejects ITM results that are failed or NaN."""

    def test_failed_itm_result_raises_exception(self, monkeypatch):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = _make_p2p_params()
        params.clutter_enabled = False
        params.clutter_grid = None
        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
        monkeypatch.setattr(
            p2p_compute,
            "itm_p2p_loss",
            lambda **_kwargs: ITMResult(loss_db=float("nan"), mode=0, warnings=1, failed=True),
        )
        with pytest.raises(Exception, match="ITM prediction failed"):
            p2p_compute.run_p2p_analysis(params)

    def test_nan_loss_raises_exception(self, monkeypatch):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = _make_p2p_params()
        params.clutter_enabled = False
        params.clutter_grid = None
        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
        monkeypatch.setattr(
            p2p_compute,
            "itm_p2p_loss",
            lambda **_kwargs: ITMResult(loss_db=float("nan"), mode=0, warnings=1, failed=False),
        )
        with pytest.raises(Exception, match="ITM prediction failed"):
            p2p_compute.run_p2p_analysis(params)

    def test_inf_loss_raises_exception(self, monkeypatch):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = _make_p2p_params()
        params.clutter_enabled = False
        params.clutter_grid = None
        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
        monkeypatch.setattr(
            p2p_compute,
            "itm_p2p_loss",
            lambda **_kwargs: ITMResult(loss_db=float("inf"), mode=0, warnings=1, failed=False),
        )
        with pytest.raises(Exception, match="ITM prediction failed"):
            p2p_compute.run_p2p_analysis(params)


class TestITMLossUpperBoundInConstants:
    """Verify that ITM_LOSS_UPPER_BOUND is defined and accessible from constants."""

    def test_itm_loss_upper_bound_is_400(self):
        assert ITM_LOSS_UPPER_BOUND == 400.0

    def test_itm_loss_upper_bound_is_numeric(self):
        assert isinstance(ITM_LOSS_UPPER_BOUND, float)


class TestP2PITMLossCapConsistency:
    """Verify the ITM cap is visible consistently across vector layer, chart, and feedback."""

    def _run_capped(self, monkeypatch, raw_loss=999.0):
        p2p_compute = _load_p2p_compute_with_test_stubs(monkeypatch)
        params = _make_p2p_params()
        params.clutter_enabled = False
        params.clutter_grid = None
        monkeypatch.setattr(p2p_compute, "ElevationGrid", _ElevationGrid)
        monkeypatch.setattr(
            p2p_compute, "itm_p2p_loss",
            lambda **_kw: ITMResult(loss_db=raw_loss, mode=2, warnings=0),
        )
        monkeypatch.setattr(p2p_compute, "antenna_gain_adjustment_db", lambda *a, **kw: 0.0)
        monkeypatch.setattr(p2p_compute, "_load_p2p_qgis_layers", lambda *a, **kw: None)
        monkeypatch.setattr(p2p_compute, "_write_p2p_reports", lambda *a, **kw: None)
        captured = {}
        monkeypatch.setattr(
            p2p_compute, "build_p2p_report_payload",
            lambda *a, **kw: (captured.update(kw) or {"results": {"itm_path_loss_db": kw["itm_loss_db"],
                "free_space_loss_db": 100.0, "total_path_loss_db": kw["itm_loss_db"],
                "eirp_dbm": 37.0, "clutter_tx_db": 0.0, "clutter_rx_db": 0.0,
                "received_power_dbm": -63.0, "link_margin_db": 27.0,
                "propagation_mode_name": "Diffraction", "antenna_gain_adjustment_db": 0.0,
                "fade_margin_class": "good", "reliability_summary": "OK",
                "availability_method": "n/a", "availability_estimate_pct": None,
                "fresnel_1_violated": False, "fresnel_60_violated": False,
                "max_fresnel_radius_m": 10.0, "tx_cch_m": 0.0, "rx_cch_m": 0.0,
                "clutter_method": "", "clutter_percentile": 50.0, "bel_rx_db": 0.0},
                "inputs": {"tx_lat": 0, "tx_lon": 0, "rx_lat": 0, "rx_lon": 0,
                    "tx_height_m": 30.0, "rx_height_m": 10.0, "frequency_mhz": 900.0,
                    "polarization": "H", "climate": "1", "k_factor": 1.333,
                    "tx_power_dbm": 30.0, "tx_gain_dbi": 10.0, "rx_gain_dbi": 8.0,
                    "cable_loss_db": 1.0, "rx_sensitivity_dbm": -90.0,
                    "tx_antenna_preset": "omni", "rx_antenna_preset": "omni",
                    "clutter_source": "off"},
                "status": {"summary": "VIABLE", "viable": True}}),
        )
        write_args = {}
        monkeypatch.setattr(
            p2p_compute, "_write_p2p_output_layers",
            lambda *a, **kw: (write_args.update(kw) or
                              ("/tmp/p.gpkg", "/tmp/f.gpkg", "/tmp/m.gpkg")),
        )

        class _CapturingFeedback:
            def __init__(self):
                self.messages = []
            def pushInfo(self, m):
                self.messages.append(m)
            def setProgress(self, _):
                pass

        fb = _CapturingFeedback()
        params.feedback = fb
        p2p_compute.run_p2p_analysis(params)
        return captured, write_args, fb

    def test_vector_layer_receives_capped_loss(self, monkeypatch):
        _, write_args, _ = self._run_capped(monkeypatch)
        assert write_args.get("itm_loss_db") == ITM_LOSS_UPPER_BOUND

    def test_feedback_log_shows_capped_loss(self):
        from NoWires.p2p_report_display import report_p2p_results

        class _CapturingFeedback:
            def __init__(self):
                self.messages = []
            def pushInfo(self, m):
                self.messages.append(m)
            def setProgress(self, _):
                pass

        fb = _CapturingFeedback()
        result = SimpleNamespace(loss_db=999.0, mode=2)
        payload = {
            "inputs": {"tx_power_dbm": 30.0, "tx_gain_dbi": 10.0, "cable_loss_db": 1.0,
                       "rx_gain_dbi": 8.0, "rx_sensitivity_dbm": -90.0},
            "results": {"itm_path_loss_db": ITM_LOSS_UPPER_BOUND,
                        "free_space_loss_db": 100.0, "total_path_loss_db": ITM_LOSS_UPPER_BOUND,
                        "eirp_dbm": 37.0, "clutter_tx_db": 0.0, "clutter_rx_db": 0.0,
                        "received_power_dbm": -63.0, "link_margin_db": 27.0,
                        "propagation_mode_name": "Diffraction",
                        "antenna_gain_adjustment_db": 0.0, "fade_margin_class": "good",
                        "reliability_summary": "OK", "availability_method": "n/a",
                        "availability_estimate_pct": None,
                        "fresnel_1_violated": False, "fresnel_60_violated": False},
        }
        report_p2p_results(fb, dist_m=5000.0, f_mhz=900.0, result=result,
                           report_payload=payload, k_factor=1.333,
                           los_blocked=False, fresnel_r_max=25.0)
        itm_lines = [m for m in fb.messages if "ITM Path Loss" in m]
        assert itm_lines, "no 'ITM Path Loss' line in feedback"
        assert "{:.2f}".format(ITM_LOSS_UPPER_BOUND) in itm_lines[0]
        assert "999" not in itm_lines[0]

    def test_chart_status_text_uses_capped_loss(self):
        from NoWires.p2p_chart_format import build_chart_status_text
        result = SimpleNamespace(loss_db=999.0)
        text = build_chart_status_text(result, prx_dbm=-63.0, margin_db=27.0,
                                       itm_loss_db=ITM_LOSS_UPPER_BOUND)
        assert "{:.1f}".format(ITM_LOSS_UPPER_BOUND) in text
        assert "999" not in text

    def test_chart_status_text_falls_back_without_itm_loss_db(self):
        from NoWires.p2p_chart_format import build_chart_status_text
        result = SimpleNamespace(loss_db=150.0)
        text = build_chart_status_text(result, prx_dbm=-80.0, margin_db=10.0)
        assert "150.0" in text
