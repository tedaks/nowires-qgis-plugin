# -*- coding: utf-8 -*-
"""
Optional numba-accelerated color mapping for coverage rasters.

Provides a vectorized RGBA color application kernel using numba parallel JIT.
If numba is unavailable, falls back to a pure-Python implementation.
"""

import math

try:
    import numba
    import numpy as _np

    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False
    numba = None
    _np = None


if _HAS_NUMBA:

    @numba.jit(nopython=True, parallel=True, cache=True)
    def apply_coverage_colors(
        prx_grid: _np.ndarray,
        thresholds: _np.ndarray,
        colors: _np.ndarray,
        rgba_out: _np.ndarray,
    ) -> None:
        rows, cols = prx_grid.shape
        n_thresh = len(thresholds)
        for i in numba.prange(rows):
            out_row = rows - 1 - i
            for j in range(cols):
                v = prx_grid[i, j]
                if _np.isnan(v):
                    rgba_out[out_row, j, 0] = 0
                    rgba_out[out_row, j, 1] = 0
                    rgba_out[out_row, j, 2] = 0
                    rgba_out[out_row, j, 3] = 0
                    continue
                k = n_thresh
                for t_idx in range(n_thresh):
                    if v >= thresholds[t_idx]:
                        k = t_idx
                        break
                rgba_out[out_row, j, 0] = colors[k, 0]
                rgba_out[out_row, j, 1] = colors[k, 1]
                rgba_out[out_row, j, 2] = colors[k, 2]
                rgba_out[out_row, j, 3] = colors[k, 3]

else:

    def apply_coverage_colors(prx_grid, thresholds, colors, rgba_out):
        rows, cols = prx_grid.shape
        n_thresh = len(thresholds)
        for i in range(rows):
            out_row = rows - 1 - i
            for j in range(cols):
                v = prx_grid[i, j]
                if math.isnan(v):
                    rgba_out[out_row, j] = [0, 0, 0, 0]
                    continue
                k = n_thresh
                for t_idx in range(n_thresh):
                    if v >= thresholds[t_idx]:
                        k = t_idx
                        break
                rgba_out[out_row, j] = colors[k]
