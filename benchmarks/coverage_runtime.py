# -*- coding: utf-8 -*-
"""Small benchmark for the coverage-analysis runtime."""

from __future__ import annotations

import argparse
import math
import os
import sys
import types
from dataclasses import dataclass
from time import perf_counter

import numpy as np

if __package__ in (None, ""):
    _plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _package = sys.modules.setdefault("NoWires", types.ModuleType("NoWires"))
    _package.__path__ = [_plugin_dir]
    _package.__package__ = "NoWires"
    from NoWires.coverage_engine import compute_coverage
    from NoWires.benchmarks.reference_cases import CoverageCase, COVERAGE_CASES, SyntheticElevationGrid
else:
    from ..coverage_engine import compute_coverage
    from .reference_cases import CoverageCase, COVERAGE_CASES, SyntheticElevationGrid


DEFAULT_CASES = COVERAGE_CASES

BenchmarkCase = CoverageCase


def run_case(case: CoverageCase):
    grid = SyntheticElevationGrid(case.radius_km)
    start = perf_counter()
    prx_grid, _, _, _, _, _, _, _ = compute_coverage(
        elev_grid=grid,
        tx_lat=0.0,
        tx_lon=0.0,
        tx_h_m=30.0,
        rx_h_m=10.0,
        f_mhz=case.frequency_mhz,
        radius_km=case.radius_km,
        grid_size=case.grid_size,
    )
    elapsed_s = perf_counter() - start
    pixels = int(np.count_nonzero(~np.isnan(prx_grid)))
    pixels_per_second = pixels / elapsed_s if elapsed_s > 0 else math.inf
    return {
        "label": case.label,
        "radius_km": case.radius_km,
        "grid_size": case.grid_size,
        "frequency_mhz": case.frequency_mhz,
        "pixels": pixels,
        "elapsed_s": round(elapsed_s, 3),
        "pixels_per_second": round(pixels_per_second, 1),
    }


def format_results(results):
    header = "label  grid  radius_km  freq_mhz  pixels  elapsed_s  pixels_per_second"
    rows = [header]
    for result in results:
        rows.append(
            "{label:<5}  {grid_size:>4}  {radius_km:>9.1f}  {frequency_mhz:>8.1f}  "
            "{pixels:>6}  {elapsed_s:>9.3f}  {pixels_per_second:>17.1f}".format(
                **result
            )
        )
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        choices=[case.label for case in DEFAULT_CASES],
        help="Run one or more named benchmark cases (default: all).",
    )
    args = parser.parse_args(argv)

    selected = set(args.case or [])
    cases = [case for case in DEFAULT_CASES if not selected or case.label in selected]
    results = [run_case(case) for case in cases]
    print(format_results(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
