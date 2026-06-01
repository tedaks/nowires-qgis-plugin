# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for AttributeError when antenna config is None.

Before the fix, antenna_gain_adjustment_db() accessed config.preset
without a null check, crashing on NoneType when the dataclass default
(tx_antenna_config=None, rx_antenna_config=None) was passed.
"""
from antenna import AntennaConfig, antenna_gain_adjustment_db


def test_none_config_returns_zero():
    assert antenna_gain_adjustment_db(0.0, 0.0, None) == 0.0


def test_none_config_negative_bearing():
    assert antenna_gain_adjustment_db(-45.0, 10.0, None) == 0.0


def test_omni_config_still_returns_zero():
    config = AntennaConfig(preset="omni")
    assert antenna_gain_adjustment_db(0.0, 0.0, config) == 0.0