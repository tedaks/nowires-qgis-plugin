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
else:
    from ..coverage_engine import compute_coverage


@dataclass(frozen=True)
class BenchmarkCase:
    label: str
    radius_km: float
    grid_size: int
    frequency_mhz: float


DEFAULT_CASES = (
    BenchmarkCase("small", radius_km=2.0, grid_size=64, frequency_mhz=900.0),
    BenchmarkCase("medium", radius_km=5.0, grid_size=128, frequency_mhz=1800.0),
    BenchmarkCase("large", radius_km=8.0, grid_size=192, frequency_mhz=3500.0),
)


class SyntheticElevationGrid:
    """Deterministic in-memory DEM for repeatable benchmark runs."""

    def __init__(self, radius_km: float, samples: int = 512):
        radius_deg = radius_km / 111.32
        self.min_lat = -radius_deg
        self.max_lat = radius_deg
        self.min_lon = -radius_deg
        self.max_lon = radius_deg
        self.n_rows = samples
        self.n_cols = samples

        ys = np.linspace(-1.0, 1.0, samples, dtype=np.float32)
        xs = np.linspace(-1.0, 1.0, samples, dtype=np.float32)
        xg, yg = np.meshgrid(xs, ys)
        ridge = 180.0 * np.exp(-3.5 * (xg * xg + yg * yg))
        ripple = 35.0 * np.sin(8.0 * xg) * np.cos(6.0 * yg)
        slope = 25.0 * (xg + yg)
        self.data = (ridge + ripple + slope + 120.0).astype(np.float32)

    def grid_meta_dict(self):
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
            "n_lat": self.n_rows,
            "n_lon": self.n_cols,
        }


def run_case(case: BenchmarkCase):
    grid = SyntheticElevationGrid(case.radius_km)
    start = perf_counter()
    prx_grid, _, _, _, _, _ = compute_coverage(
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
