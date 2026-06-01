# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: validate_itm_input_ranges must validate percentages, k_factor, epsilon.

The v1.7.1 fail-fast validation extends validate_itm_input_ranges to also
check time/location/situation percentages, k_factor, and epsilon before the
DEM download.
"""

import pytest
from NoWires.radio import validate_itm_input_ranges


def test_reject_time_pct_below_range():
    with pytest.raises(ValueError, match="Time percentage"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            time_pct=0.0,
        )


def test_reject_time_pct_above_range():
    with pytest.raises(ValueError, match="Time percentage"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            time_pct=100.0,
        )


def test_reject_location_pct_below_range():
    with pytest.raises(ValueError, match="Location percentage"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            location_pct=-1.0,
        )


def test_reject_situation_pct_above_range():
    with pytest.raises(ValueError, match="Situation percentage"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            situation_pct=100.0,
        )


def test_reject_k_factor_below_range():
    with pytest.raises(ValueError, match="K-factor"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            k_factor=-1.0,
        )


def test_reject_k_factor_zero():
    with pytest.raises(ValueError, match="K-factor"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            k_factor=0.0,
        )


def test_reject_epsilon_below_range():
    with pytest.raises(ValueError, match="Earth permittivity epsilon"):
        validate_itm_input_ranges(
            tx_height_m=30, rx_height_m=10, frequency_mhz=300,
            surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
            epsilon=0.5,
        )


def test_accept_valid_extended_params():
    validate_itm_input_ranges(
        tx_height_m=30, rx_height_m=10, frequency_mhz=300,
        surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
        time_pct=50.0, location_pct=50.0, situation_pct=50.0,
        k_factor=1.33, epsilon=15.0,
    )


def test_optional_params_default_none():
    validate_itm_input_ranges(
        tx_height_m=30, rx_height_m=10, frequency_mhz=300,
        surface_refractivity_n0=301, earth_conductivity_sigma=0.005,
    )