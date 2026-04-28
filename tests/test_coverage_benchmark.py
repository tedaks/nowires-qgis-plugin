# -*- coding: utf-8 -*-
"""Regression tests for the coverage benchmark helper."""

import importlib

import numpy as np
import pytest


def test_benchmark_module_exists():
    module = importlib.import_module("NoWires.benchmarks.coverage_runtime")
    assert hasattr(module, "run_case")


def test_run_case_reports_elapsed_and_pixels(monkeypatch):
    module = importlib.import_module("NoWires.benchmarks.coverage_runtime")

    monkeypatch.setattr(module, "perf_counter", iter([10.0, 10.5]).__next__)

    calls = {}

    def fake_compute_coverage(**kwargs):
        calls["kwargs"] = kwargs
        grid_size = kwargs["grid_size"]
        return (
            np.full((grid_size, grid_size), -80.0, dtype=np.float32),
            np.full((grid_size, grid_size), 120.0, dtype=np.float32),
            -0.01,
            0.01,
            -0.01,
            0.01,
            np.full((grid_size, grid_size), 0.0, dtype=np.float32),
            np.full((grid_size, grid_size), 0.0, dtype=np.float32),
        )

    monkeypatch.setattr(module, "compute_coverage", fake_compute_coverage)

    from NoWires.benchmarks.reference_cases import CoverageCase
    case = CoverageCase(label="smoke", radius_km=1.0, grid_size=8, frequency_mhz=900.0)
    result = module.run_case(case)

    assert calls["kwargs"]["grid_size"] == 8
    assert result["label"] == "smoke"
    assert result["grid_size"] == 8
    assert result["pixels"] == 64
    assert result["elapsed_s"] == 0.5
    assert result["pixels_per_second"] == 128.0


@pytest.mark.benchmark
def test_coverage_small_case_loads():
    from NoWires.benchmarks.reference_cases import COVERAGE_CASES
    case = next(c for c in COVERAGE_CASES if c.label == "small")
    assert case.radius_km == 2.0
    assert case.grid_size == 64


@pytest.mark.benchmark
def test_coverage_medium_case_loads():
    from NoWires.benchmarks.reference_cases import COVERAGE_CASES
    case = next(c for c in COVERAGE_CASES if c.label == "medium")
    assert case.radius_km == 5.0
    assert case.grid_size == 128
