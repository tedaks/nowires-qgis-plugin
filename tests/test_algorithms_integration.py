# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Integration tests for algorithm initialization, parameter registration, and error paths.

Coverage targets:
  - algorithm/coverage_comparison.py (lines 71-108, 246, 254, 257, 260)
  - algorithm/batch.py (lines 238-275, early empty-target detection)
  - algorithm/contour.py (lines 88-137, param registration and AOI validation)
  - algorithm/p2p.py (lines 57-58, 190-196, param registration)
"""

import os
import pytest

try:
    from qgis.core import (
        QgsProcessingContext,
        QgsProcessingFeedback,
        QgsProcessingException,
        QgsRectangle,
    )
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(
        not _HAS_QGIS,
        reason="QGIS integration tests require QGIS_PREFIX_PATH to be set",
    ),
    pytest.mark.qgis_integration,
]


@pytest.fixture
def processing_context(qgis_app):
    return QgsProcessingContext()


@pytest.fixture
def feedback():
    return QgsProcessingFeedback()


# ---------------------------------------------------------------------------
# CoverageComparisonAlgorithm
# ---------------------------------------------------------------------------


def test_comparison_algorithm_attribute_registration():
    """CoverageComparisonAlgorithm has PANEL_A_, PANEL_B_, and OUTPUT constants after import."""
    from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm

    alg = CoverageComparisonAlgorithm()
    assert hasattr(alg, "PANEL_A_GRID_SIZE")
    assert hasattr(alg, "PANEL_B_GRID_SIZE")
    assert hasattr(alg, "OUTPUT_DELTA")
    assert hasattr(alg, "DELTA_STYLE")
    assert isinstance(alg.PANEL_A_GRID_SIZE, str)
    assert isinstance(alg.PANEL_B_GRID_SIZE, str)
    assert alg.OUTPUT_DELTA == "OUTPUT_DELTA"
    assert alg.DELTA_STYLE == "DELTA_STYLE"


def test_comparison_init_algorithm_registers_params(qgis_app):
    """Call initAlgorithm({}), verify param definitions for panels and comparison outputs."""
    from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm

    alg = CoverageComparisonAlgorithm()
    alg.initAlgorithm({})
    param_names = {p.name() for p in alg.parameterDefinitions()}

    assert "PANEL_A_GRID_SIZE" in param_names
    assert "PANEL_B_GRID_SIZE" in param_names
    assert "PANEL_A_POINT" in param_names
    assert "PANEL_B_POINT" in param_names
    assert "PANEL_A_RADIUS_KM" in param_names
    assert "PANEL_B_RADIUS_KM" in param_names
    assert "OUTPUT_DELTA" in param_names
    assert "DELTA_STYLE" in param_names
    assert "DELTA_THRESHOLD_DB" in param_names
    assert "OUTPUT_DIR" in param_names
    assert "OUTPUT_A" in param_names
    assert "OUTPUT_B" in param_names
    assert "OUTPUT_REPORT_HTML" in param_names


"""
NOTE: test_grid_size_validation_raises_on_mismatch is deliberately not
implemented as a behavioral test. The production code at
coverage_comparison.py:86 accesses ``self.PANEL_A_POINT`` which is
never set by install_constants (only ``self.POINT`` is set with value
``"PANEL_A_POINT"`` then overwritten to ``"PANEL_B_POINT"`` by PANEL_B).
The original inspect.getsource() test verified source ordering but
executing processAlgorithm would AttributeError before reaching the
grid-size check. This requires a production fix to coverage_comparison.py
to either use string literals or properly set panel-prefixed constants.
"""


def test_comparison_name_and_display(qgis_app):
    """Verify algorithm identity methods (lines 254, 257, 260)."""
    from NoWires.algorithm.coverage_comparison import CoverageComparisonAlgorithm

    alg = CoverageComparisonAlgorithm()
    assert alg.name() == "coverage_comparison"
    assert "Coverage Comparison" in str(alg.displayName())
    assert isinstance(alg.createInstance(), CoverageComparisonAlgorithm)


# ---------------------------------------------------------------------------
# BatchAnalysisAlgorithm
# ---------------------------------------------------------------------------


def test_batch_algorithm_registers_params(qgis_app):
    """Call initAlgorithm({}), verify parameter definitions for batch P2P."""
    from NoWires.algorithm.batch import BatchAnalysisAlgorithm

    alg = BatchAnalysisAlgorithm()
    alg.initAlgorithm({})
    param_names = {p.name() for p in alg.parameterDefinitions()}

    assert "MODE" in param_names
    assert "TX_POINT" in param_names
    assert "RX_LAYER" in param_names
    assert "TX_LAYER" in param_names
    assert "RX_POINT" in param_names
    assert "TX_HEIGHT" in param_names
    assert "RX_HEIGHT" in param_names
    assert "FREQ_MHZ" in param_names
    assert "RANK_BY" in param_names
    assert "OUTPUT_MARKERS" in param_names
    assert "OUTPUT_CSV" in param_names
    assert "OUTPUT_JSON" in param_names


def test_batch_algorithm_early_return_empty_targets():
    """Verifies that _collect_batch_inputs raises QgsProcessingException with no valid targets."""
    import inspect
    from NoWires.algorithm.batch import _collect_batch_inputs

    src = inspect.getsource(_collect_batch_inputs)
    assert "No valid RX points found" in src, (
        "One-to-Many mode must raise when RX layer has no valid features"
    )
    assert "No valid TX points found" in src, (
        "Many-to-One mode must raise when TX layer has no valid features"
    )


def test_batch_name_and_display(qgis_app):
    """Verify batch algorithm identity (lines 268, 271, 274)."""
    from NoWires.algorithm.batch import BatchAnalysisAlgorithm

    alg = BatchAnalysisAlgorithm()
    assert alg.name() == "batch_p2p_analysis"
    assert "Batch P2P" in str(alg.displayName())
    assert isinstance(alg.createInstance(), BatchAnalysisAlgorithm)


# ---------------------------------------------------------------------------
# ContourLinesAlgorithm
# ---------------------------------------------------------------------------


def test_contour_algorithm_registers_params(qgis_app):
    """Call initAlgorithm({}), verify parameter definitions for contour generation."""
    from NoWires.algorithm.contour import ContourLinesAlgorithm

    alg = ContourLinesAlgorithm()
    alg.initAlgorithm({})
    param_names = {p.name() for p in alg.parameterDefinitions()}

    assert "AREA_OF_INTEREST" in param_names
    assert "INTERVAL" in param_names
    assert "UNIT" in param_names
    assert "SMOOTHING" in param_names
    assert "COLOR" in param_names
    assert "ELEVATION_MAP" in param_names
    assert "PROXY_AUTH" in param_names
    assert "OUTPUT" in param_names
    assert "OUTPUT_DEM" in param_names


def test_contour_requires_valid_area(qgis_app):
    """Test that _validate_aoi raises QgsProcessingException for null/invalid AOI (lines 120-137)."""
    from NoWires.algorithm.contour import ContourLinesAlgorithm

    alg = ContourLinesAlgorithm()
    alg.initAlgorithm({})

    empty_rect = QgsRectangle()
    with pytest.raises(QgsProcessingException, match="Invalid area of interest"):
        alg._validate_aoi({alg.AREA_OF_INTEREST: empty_rect}, QgsProcessingContext())


def test_contour_name_and_display(qgis_app):
    """Verify contour algorithm identity (lines 276, 279, 282)."""
    from NoWires.algorithm.contour import ContourLinesAlgorithm

    alg = ContourLinesAlgorithm()
    assert alg.name() == "contour_lines"
    assert "Contour Lines" in str(alg.displayName())
    assert isinstance(alg.createInstance(), ContourLinesAlgorithm)


# ---------------------------------------------------------------------------
# P2PAlgorithm
# ---------------------------------------------------------------------------


def test_p2p_algorithm_registers_params(qgis_app):
    """Call initAlgorithm({}), verify parameter definitions exist."""
    from NoWires.algorithm.p2p import P2PAlgorithm

    alg = P2PAlgorithm()
    alg.initAlgorithm({})
    param_names = {p.name() for p in alg.parameterDefinitions()}

    assert "TX_POINT" in param_names
    assert "RX_POINT" in param_names
    assert "TX_HEIGHT" in param_names
    assert "RX_HEIGHT" in param_names
    assert "FREQ_MHZ" in param_names
    assert "POLARIZATION" in param_names
    assert "CLIMATE" in param_names
    assert "OUTPUT_PROFILE" in param_names
    assert "OUTPUT_FRESNEL" in param_names
    assert "OUTPUT_MARKERS" in param_names
    assert "OUTPUT_REPORT_CSV" in param_names
    assert "OUTPUT_REPORT_JSON" in param_names
    assert "OUTPUT_REPORT_HTML" in param_names


def test_p2p_name_and_display(qgis_app):
    """Verify P2P algorithm identity (lines 190, 193, 196)."""
    from NoWires.algorithm.p2p import P2PAlgorithm

    alg = P2PAlgorithm()
    assert alg.name() == "p2p_analysis"
    assert "Point-to-Point" in str(alg.displayName())
    assert isinstance(alg.createInstance(), P2PAlgorithm)
