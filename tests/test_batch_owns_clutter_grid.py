# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for batch clutter-grid ownership (v1.5.7 fix #5).

Before v1.5.7, algorithm_batch.processAlgorithm unconditionally closed
inp.clutter_grid in its finally block, even when the grid was user-provided
(via CLUTTER_RASTER). This mirrors the v1.5.0/v1.5.1 fix for P2P/Coverage.
The fix adds an owns_clutter_grid flag set only when the grid was
auto-downloaded.
"""



def test_batch_params_dataclass_has_owns_clutter_grid():
    """BatchAnalysisParams must include an owns_clutter_grid field."""
    from batch.analysis_params import BatchAnalysisParams

    params = BatchAnalysisParams()
    assert hasattr(params, "owns_clutter_grid"), (
        "BatchAnalysisParams must have owns_clutter_grid field"
    )
    assert params.owns_clutter_grid is False, (
        "Default for owns_clutter_grid should be False"
    )


def test_batch_analysis_params_owns_clutter_grid_default():
    """owns_clutter_grid must default to False, not True."""
    from batch.analysis_params import BatchAnalysisParams

    p = BatchAnalysisParams()
    assert p.owns_clutter_grid is False