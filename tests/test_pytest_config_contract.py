# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for root-level pytest configuration discovery."""

from pathlib import Path


def test_benchmark_marker_registered_at_repo_root():
    root_pytest_ini = Path(__file__).resolve().parent.parent / "pytest.ini"
    assert root_pytest_ini.exists()
    text = root_pytest_ini.read_text(encoding="utf-8")
    assert "benchmark: marks tests as benchmark" in text

