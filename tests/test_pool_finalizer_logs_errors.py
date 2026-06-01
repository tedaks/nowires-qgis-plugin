# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test: _final_cov_pool logs SharedMemory errors instead of silently swallowing."""

import logging

import numpy as np


def test_finalizer_logs_permission_error_on_unlink(caplog, monkeypatch):
    """_final_cov_pool should log PermissionError (OSError) at DEBUG level."""
    import radio_coverage.pool as rcp
    from unittest.mock import MagicMock

    caplog.set_level(logging.DEBUG, logger="NoWires.radio_coverage.pool")

    mock_shm = MagicMock()
    mock_shm.close.side_effect = None
    mock_shm.unlink.side_effect = PermissionError("access denied")

    old_shm = rcp._cov_shm
    old_data = rcp._cov_grid_data
    rcp._cov_shm = mock_shm
    rcp._cov_grid_data = np.array([1.0])
    try:
        rcp._final_cov_pool()
        assert rcp._cov_shm is None
        assert rcp._cov_grid_data is None
        assert any(
            "shm finalizer" in rec.message and "access denied" in rec.message
            for rec in caplog.records
        )
    finally:
        rcp._cov_shm = old_shm
        rcp._cov_grid_data = old_data


def test_finalizer_silently_ignores_filenotfound_on_unlink(caplog, monkeypatch):
    """FileNotFoundError on unlink is normal — no log entry should be emitted."""
    import radio_coverage.pool as rcp
    from unittest.mock import MagicMock

    caplog.set_level(logging.DEBUG, logger="NoWires.radio_coverage.pool")

    mock_shm = MagicMock()
    mock_shm.close.side_effect = None
    mock_shm.unlink.side_effect = FileNotFoundError("no such file")

    old_shm = rcp._cov_shm
    old_data = rcp._cov_grid_data
    rcp._cov_shm = mock_shm
    rcp._cov_grid_data = np.array([1.0])
    try:
        rcp._final_cov_pool()
        assert rcp._cov_shm is None
        assert rcp._cov_grid_data is None
        assert not any(
            "shm finalizer" in rec.message
            for rec in caplog.records
        )
    finally:
        rcp._cov_shm = old_shm
        rcp._cov_grid_data = old_data
