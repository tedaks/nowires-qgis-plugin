# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Benchmark for the P2P runtime."""

from __future__ import annotations

import argparse
import os
import sys
import types
from time import perf_counter

import numpy as np

if __package__ in (None, ""):
    _plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _package = sys.modules.setdefault("NoWires", types.ModuleType("NoWires"))
    _package.__path__ = [_plugin_dir]
    _package.__package__ = "NoWires"
    from NoWires.coverage_compute import compute_itm_p2p
    from NoWires.benchmarks.reference_cases import (
        P2PCase,
        P2P_CASES,
    )
else:
    from ..coverage_compute import compute_itm_p2p
    from .reference_cases import P2PCase, P2P_CASES


DEFAULT_CASES = P2P_CASES


def _terrain_elevations(terrain: str, distance_km: float, samples: int = 200):
    _ = distance_km * 1000.0
    if terrain == "flat":
        return np.full(samples, 120.0, dtype=np.float32)
    elif terrain == "varied":
        t = np.linspace(0.0, 1.0, samples, dtype=np.float32)
        base = 120.0 + 50.0 * np.sin(2.0 * np.pi * t * 5.0)
        base += 20.0 * np.sin(2.0 * np.pi * t * 12.0)
        return base.astype(np.float32)
    elif terrain == "coastal":
        t = np.linspace(0.0, 1.0, samples, dtype=np.float32)
        coastal = np.where(t < 0.3, 5.0, 120.0 + 30.0 * (t - 0.3) / 0.7)
        return coastal.astype(np.float32)
    return np.full(samples, 120.0, dtype=np.float32)


def run_case(case: P2PCase):
    resolution = (case.distance_km * 1000.0) / 200.0
    elevations = _terrain_elevations(case.terrain, case.distance_km, 200)
    start = perf_counter()
    result = compute_itm_p2p(
        h_tx__meter=case.tx_height_m,
        h_rx__meter=case.rx_height_m,
        elevations=elevations,
        resolution=resolution,
        climate_idx=case.climate_idx,
        N_0=301.0,
        f__mhz=case.frequency_mhz,
        polarization=case.polarization,
        epsilon=case.epsilon,
        sigma=case.sigma,
        time_pct=case.time_pct,
        location_pct=case.location_pct,
        situation_pct=case.situation_pct,
        eirp_dbm=case.eirp_dbm,
        ant_gain_adj=case.ant_gain_adj,
        rx_gain_dbi=case.rx_gain_dbi,
    )
    elapsed_s = perf_counter() - start
    loss_db = result["total_path_loss_db"] if result else float("nan")
    return {
        "label": case.label,
        "distance_km": case.distance_km,
        "terrain": case.terrain,
        "frequency_mhz": case.frequency_mhz,
        "loss_db": round(loss_db, 2),
        "elapsed_s": round(elapsed_s, 3),
    }


def format_results(results):
    header = "label  distance_km  terrain  freq_mhz  loss_db  elapsed_s"
    rows = [header]
    for result in results:
        rows.append(
            "{label:<12}  {distance_km:>11.1f}  {terrain:>7}  "
            "{frequency_mhz:>8.1f}  {loss_db:>7.2f}  {elapsed_s:>9.3f}".format(
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
