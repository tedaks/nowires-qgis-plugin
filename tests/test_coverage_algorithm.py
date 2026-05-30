# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for algorithm/coverage.py targeting missed coverage lines.

- _build_clutter_context exception-safety (Issue #14 fix, lines 72-77)
- processAlgorithm finally-block owns_clutter close (lines 264-279)
- CoverageAlgorithm constants (lines 90, 288-297)
- postProcessAlgorithm legend show (lines 190-195)
"""

from unittest import mock

import numpy as np
import pytest

from qgis.core import QgsProcessingContext, QgsProcessingFeedback

from NoWires.algorithm.coverage import _build_clutter_context, CoverageAlgorithm
from NoWires.clutter.context import TerminalClutterLosses
from NoWires.radio_coverage.analysis_params import CoverageAnalysisParams

pytestmark = pytest.mark.qgis_integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dummy_grid(source="auto"):
    """Return a LandCoverGrid-like mock that tracks close() calls."""
    g = mock.MagicMock()
    g.source = source
    return g


def _dummy_elev(tx_ground=123.0):
    """Return an elev mock whose .sample returns *tx_ground*."""
    e = mock.MagicMock()
    e.sample.return_value = tx_ground
    return e


def _fresh_algorithm():
    """Return a freshly constructed CoverageAlgorithm."""
    alg = CoverageAlgorithm()
    alg._raster_layer_ids = []
    alg._vector_layer_ids = []
    alg._coverage_post_processor = None
    alg._pending_legend_rx_sens = None
    alg._dem_layer_id = None
    alg._coverage_layer_id = None
    return alg


# ---------------------------------------------------------------------------
# Tests — _build_clutter_context exception safety (Issue #14, lines 72-77)
# ---------------------------------------------------------------------------

class TestBuildClutterContextExceptionSafety:
    """Issue #14 regression: original exception must propagate, not be
    masked by an error during grid close."""

    def test_exception_preserves_original(self, monkeypatch):
        """clutter_source_label raises ValueError — original propagates,
        and owns_grid=True triggers close(). Lines 72-73."""
        from NoWires.algorithm import _coverage_helpers as helpers_mod

        p = CoverageAnalysisParams(
            clutter_enabled=True,
            clutter_model="simple",
            tx_lat=14.0, tx_lon=121.0,
        )
        grid = _dummy_grid()
        elev = _dummy_elev()

        monkeypatch.setattr(helpers_mod, "coverage_bounds",
                            lambda *a, **kw: (10.0, 20.0, 110.0, 130.0))
        monkeypatch.setattr(helpers_mod, "ensure_clutter_grid_for_area",
                            lambda *a, **kw: grid)
        monkeypatch.setattr(helpers_mod, "compute_terminal_clutter_losses",
                            lambda *a, **kw: TerminalClutterLosses(
                                "open", "open", 0.0, 0.0, 0.0, "mock"))
        monkeypatch.setattr(helpers_mod, "clutter_source_label",
                            mock.Mock(side_effect=ValueError("simulated")))

        with pytest.raises(ValueError, match="simulated"):
            _build_clutter_context(p, None, elev)

        grid.close.assert_called_once()

    def test_closes_grid_on_source_label_failure(self, monkeypatch):
        """clutter_source_label raises RuntimeError; owns_grid=True => close.
        Lines 75-76."""
        from NoWires.algorithm import _coverage_helpers as helpers_mod

        p = CoverageAnalysisParams(
            clutter_enabled=True,
            clutter_model="simple",
            tx_lat=14.0, tx_lon=121.0,
        )
        grid = _dummy_grid()
        elev = _dummy_elev()

        monkeypatch.setattr(helpers_mod, "coverage_bounds",
                            lambda *a, **kw: (10.0, 20.0, 110.0, 130.0))
        monkeypatch.setattr(helpers_mod, "ensure_clutter_grid_for_area",
                            lambda *a, **kw: grid)
        monkeypatch.setattr(helpers_mod, "compute_terminal_clutter_losses",
                            lambda *a, **kw: TerminalClutterLosses(
                                "open", "open", 0.0, 0.0, 0.0, "mock"))
        monkeypatch.setattr(helpers_mod, "clutter_source_label",
                            mock.Mock(side_effect=RuntimeError("fail")))

        with pytest.raises(RuntimeError, match="fail"):
            _build_clutter_context(p, None, elev)

        grid.close.assert_called_once()

    def test_close_failure_does_not_mask_original(self, monkeypatch):
        """grid.close() itself raises — original ValueError still propagates.
        Lines 75-77."""
        from NoWires.algorithm import _coverage_helpers as helpers_mod

        p = CoverageAnalysisParams(
            clutter_enabled=True,
            clutter_model="simple",
            tx_lat=14.0, tx_lon=121.0,
        )
        grid = _dummy_grid()
        grid.close.side_effect = RuntimeError("close boom")
        elev = _dummy_elev()

        monkeypatch.setattr(helpers_mod, "coverage_bounds",
                            lambda *a, **kw: (10.0, 20.0, 110.0, 130.0))
        monkeypatch.setattr(helpers_mod, "ensure_clutter_grid_for_area",
                            lambda *a, **kw: grid)
        monkeypatch.setattr(helpers_mod, "compute_terminal_clutter_losses",
                            lambda *a, **kw: TerminalClutterLosses(
                                "open", "open", 0.0, 0.0, 0.0, "mock"))
        monkeypatch.setattr(helpers_mod, "clutter_source_label",
                            mock.Mock(side_effect=ValueError("original boom")))

        with pytest.raises(ValueError, match="original boom"):
            _build_clutter_context(p, None, elev)

    def test_build_initial_clutter_context_called_when_clutter_enabled(self, monkeypatch):
        """build_initial_clutter_context is called when clutter_enabled=True."""
        from NoWires.algorithm import _coverage_helpers as helpers_mod

        p = CoverageAnalysisParams(
            clutter_enabled=True,
            clutter_model="simple",
            tx_lat=14.0, tx_lon=121.0,
        )
        grid = _dummy_grid()
        elev = _dummy_elev(tx_ground=0.0)

        call_count = []

        def _fake_build_ctx(**kw):
            call_count.append(1)
            return mock.MagicMock()

        monkeypatch.setattr(helpers_mod, "coverage_bounds",
                            lambda *a, **kw: (10.0, 20.0, 110.0, 130.0))
        monkeypatch.setattr(helpers_mod, "ensure_clutter_grid_for_area",
                            lambda *a, **kw: grid)
        monkeypatch.setattr(helpers_mod, "clutter_source_label",
                            lambda **kw: "mock_source")
        monkeypatch.setattr(helpers_mod, "compute_terminal_clutter_losses",
                            lambda *a, **kw: TerminalClutterLosses(
                                "open", "open", 0.0, 0.0, 0.0, "mock"))
        monkeypatch.setattr("NoWires.clutter.context.build_initial_clutter_context",
                            _fake_build_ctx)

        _build_clutter_context(p, None, elev)
        assert call_count == [1]

    def test_ensure_clutter_grid_for_area_called_when_enabled(self, monkeypatch):
        """When clutter_enabled=True and no grid provided,
        ensure_clutter_grid_for_area is called. Lines 40-43."""
        from NoWires.algorithm import _coverage_helpers as helpers_mod

        p = CoverageAnalysisParams(
            clutter_enabled=True,
            clutter_model="simple",
            tx_lat=14.0, tx_lon=121.0,
        )
        grid = _dummy_grid()
        elev = _dummy_elev()

        ensure_calls = []
        monkeypatch.setattr(helpers_mod, "coverage_bounds",
                            lambda *a, **kw: (10.0, 20.0, 110.0, 130.0))
        monkeypatch.setattr(helpers_mod, "ensure_clutter_grid_for_area",
                            lambda **kw: ensure_calls.append(kw) or grid)
        monkeypatch.setattr(helpers_mod, "clutter_source_label",
                            lambda **kw: "mock_source")
        monkeypatch.setattr(helpers_mod, "compute_terminal_clutter_losses",
                            lambda *a, **kw: TerminalClutterLosses(
                                "open", "open", 0.0, 0.0, 0.0, "mock"))

        _build_clutter_context(p, None, elev)
        assert len(ensure_calls) == 1


# ---------------------------------------------------------------------------
# Tests — processAlgorithm finally block (owns_clutter close, lines 264-279)
# ---------------------------------------------------------------------------

class TestProcessAlgorithmOwnsClutterFinally:
    """The finally block in processAlgorithm must close auto-downloaded
    clutter grids when _owns_clutter=True."""

    def _setup_process_mocks(self, monkeypatch):
        """Shared monkeypatching for processAlgorithm tests."""
        monkeypatch.setattr(
            "NoWires.temp_manager.TempDirManager.__init__",
            lambda self: setattr(self, "_dirs", []),
        )
        monkeypatch.setattr(
            "NoWires.temp_manager.TempDirManager.cleanup", lambda self: None)
        monkeypatch.setattr(
            "NoWires.temp_manager.TempDirManager.warn_persistent",
            lambda self, fb: None)
        monkeypatch.setattr(
            "NoWires.temp_manager.TempDirManager.make_dir",
            lambda self, name, persistent=False: "/tmp/dummy_coverage")
        monkeypatch.setattr(
            "NoWires.algorithm.coverage.ensure_dem_for_area",
            lambda *a, **kw: "/fake/dem.tif")

        from NoWires.elevation import ElevationGrid
        for attr, val in [("__init__", lambda self, path: None),
                          ("__enter__", lambda self: self),
                          ("__exit__", lambda self, *a: None),
                          ("sample", lambda self, lat, lon: 50.0)]:
            monkeypatch.setattr(ElevationGrid, attr, val)
        monkeypatch.setattr(
            "NoWires.algorithm.coverage.validate_dem_coverage",
            lambda *a, **kw: None)
        monkeypatch.setattr(
            "NoWires.algorithm.coverage.extract_coverage_params",
            lambda alg_obj, prm, ctx: CoverageAnalysisParams(
                tx_lat=14.0, tx_lon=121.0, grid_size=64))

    def test_finally_closes_auto_grid_on_compute_result_none(self, monkeypatch):
        """compute_coverage returns None → QgsProcessingException,
        but finally still closes owns_clutter grid. Lines 264-267, 276-278."""
        self._setup_process_mocks(monkeypatch)

        grid = _dummy_grid()

        monkeypatch.setattr(
            "NoWires.algorithm.coverage._build_clutter_context",
            lambda p, cg, elev: (grid, None, "s", TerminalClutterLosses(
                "open", "open", 0.0, 0.0, 0.0, "mock"), True))
        monkeypatch.setattr(
            "NoWires.algorithm.coverage.compute_coverage",
            lambda **kw: None)

        alg = _fresh_algorithm()

        from qgis.core import QgsProcessingException
        with pytest.raises(QgsProcessingException, match="cancelled"):
            alg.processAlgorithm({"TX_POINT": "0,0"}, QgsProcessingContext(),
                                QgsProcessingFeedback())

        grid.close.assert_called_once()

    def test_finally_closes_auto_grid_on_unexpected_error(self, monkeypatch):
        """Unhandled MemoryError in compute_coverage → finally still closes.
        Lines 276-278."""
        self._setup_process_mocks(monkeypatch)

        grid = _dummy_grid()

        monkeypatch.setattr(
            "NoWires.algorithm.coverage._build_clutter_context",
            lambda p, cg, elev: (grid, None, "s", TerminalClutterLosses(
                "open", "open", 0.0, 0.0, 0.0, "mock"), True))
        monkeypatch.setattr(
            "NoWires.algorithm.coverage.compute_coverage",
            mock.Mock(side_effect=MemoryError("simulated OOM")))

        alg = _fresh_algorithm()

        with pytest.raises(MemoryError, match="simulated OOM"):
            alg.processAlgorithm({"TX_POINT": "0,0"}, QgsProcessingContext(),
                                QgsProcessingFeedback())

        grid.close.assert_called_once()

    def test_finally_skips_close_when_owns_clutter_false(self, monkeypatch):
        """owns_clutter=False → finally must not close the grid.  Line 276."""
        self._setup_process_mocks(monkeypatch)

        grid = _dummy_grid()
        fake_result = mock.MagicMock()
        fake_result.prx_grid = np.array([[1.0]], dtype=np.float32)

        monkeypatch.setattr(
            "NoWires.algorithm.coverage._build_clutter_context",
            lambda p, cg, elev: (grid, None, "s", TerminalClutterLosses(
                "open", "open", 0.0, 0.0, 0.0, "mock"), False))
        monkeypatch.setattr(
            "NoWires.algorithm.coverage.compute_coverage",
            lambda **kw: fake_result)
        # Mock _write_coverage_outputs to bypass all QGIS layer machinery
        monkeypatch.setattr(
            "NoWires.algorithm.coverage._write_coverage_outputs",
            lambda *a, **kw: {"OUTPUT_RASTER": "/fake/out.tif"})

        alg = _fresh_algorithm()
        result = alg.processAlgorithm({"TX_POINT": "0,0"},
                                      QgsProcessingContext(),
                                      QgsProcessingFeedback())
        assert isinstance(result, dict)
        grid.close.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — CoverageAlgorithm constants and attributes (lines 90, 178-188, 288-297)
# ---------------------------------------------------------------------------

class TestCoverageAlgorithmConstants:
    """CoverageAlgorithm must have OUTPUT_* and parameter constants after
    construction (install_constants at line 297)."""

    def test_output_constants_registered(self):
        alg = CoverageAlgorithm()
        for attr in ("OUTPUT_RASTER", "OUTPUT_REPORT_CSV", "OUTPUT_REPORT_JSON",
                     "OUTPUT_REPORT_HTML", "OUTPUT_REPORT_PDF"):
            assert hasattr(alg, attr), f"Missing {attr}"
            assert isinstance(getattr(alg, attr), str)

    def test_parameter_constants_registered(self):
        alg = CoverageAlgorithm()
        for attr in ("TX_POINT", "TX_HEIGHT", "RX_HEIGHT", "FREQ_MHZ", "RADIUS_KM",
                     "GRID_SIZE", "POLARIZATION", "CLIMATE"):
            assert hasattr(alg, attr), f"Missing {attr}"

    def test_instance_attributes_after_init(self):
        """Lines 178-186: __init__ sets _raster_layer_ids, _vector_layer_ids,
        _coverage_post_processor, and implicitly _coverage_layer_id."""
        alg = CoverageAlgorithm()
        assert alg.ALLOW_THREADING is True
        assert alg._raster_layer_ids == []
        assert alg._vector_layer_ids == []
        assert alg._coverage_post_processor is None

    def test_name_and_display_name(self):
        """Lines 288-295: name() and displayName() are defined and callable."""
        alg = CoverageAlgorithm()
        assert alg.name() == "coverage_analysis"
        result = alg.displayName()
        assert result is not None  # mock env: QCoreApplication.translate returns MagicMock

    def test_create_instance_returns_coverage_algorithm(self):
        """Line 294: createInstance()."""
        alg = CoverageAlgorithm()
        inst = alg.createInstance()
        assert isinstance(inst, CoverageAlgorithm)


# ---------------------------------------------------------------------------
# Tests — postProcessAlgorithm legend (lines 190-195)
# ---------------------------------------------------------------------------

class TestPostProcessAlgorithmLegend:
    """postProcessAlgorithm must call show_coverage_legend when
    _pending_legend_rx_sens is set."""

    def test_shows_legend_when_pending_is_set(self, monkeypatch):
        from NoWires.algorithm import coverage as cov_mod

        called_with = []

        def _fake_show(rx_sensitivity_dbm):
            called_with.append(rx_sensitivity_dbm)

        monkeypatch.setattr(cov_mod, "show_coverage_legend", _fake_show)

        alg = _fresh_algorithm()
        alg._coverage_layer_id = "dummy_cov_123"
        alg._pending_legend_rx_sens = -95.0

        result = alg.postProcessAlgorithm(QgsProcessingContext(),
                                          QgsProcessingFeedback())
        assert isinstance(result, dict)
        assert called_with == [-95.0]
        assert alg._pending_legend_rx_sens is None

    def test_skips_legend_when_pending_is_none(self, monkeypatch):
        from NoWires.algorithm import coverage as cov_mod

        called = []

        def _fake_show(rx_sensitivity_dbm):
            called.append(rx_sensitivity_dbm)

        monkeypatch.setattr(cov_mod, "show_coverage_legend", _fake_show)

        alg = _fresh_algorithm()
        alg._pending_legend_rx_sens = None

        alg.postProcessAlgorithm(QgsProcessingContext(), QgsProcessingFeedback())
        assert called == []
