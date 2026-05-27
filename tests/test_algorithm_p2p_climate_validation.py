# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: P2P algorithm must fail-fast on out-of-range climate zone."""


import pytest

from NoWires.radio import validate_itm_input_ranges, ITM_MIN_CLIMATE, ITM_MAX_CLIMATE


class TestP2PClimateRangeCheck:
    def test_climate_below_min_raises_value_error(self):
        with pytest.raises(ValueError, match="Climate zone"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=10.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=0.005,
                climate=ITM_MIN_CLIMATE - 1,
            )

    def test_climate_above_max_raises_value_error(self):
        with pytest.raises(ValueError, match="Climate zone"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=10.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=0.005,
                climate=ITM_MAX_CLIMATE + 1,
            )

    def test_climate_min_in_range_does_not_raise(self):
        validate_itm_input_ranges(
            tx_height_m=30.0,
            rx_height_m=10.0,
            frequency_mhz=300.0,
            surface_refractivity_n0=301.0,
            earth_conductivity_sigma=0.005,
            climate=ITM_MIN_CLIMATE,
        )

    def test_climate_max_in_range_does_not_raise(self):
        validate_itm_input_ranges(
            tx_height_m=30.0,
            rx_height_m=10.0,
            frequency_mhz=300.0,
            surface_refractivity_n0=301.0,
            earth_conductivity_sigma=0.005,
            climate=ITM_MAX_CLIMATE,
        )

    def test_climate_default_zero_does_not_raise(self):
        validate_itm_input_ranges(
            tx_height_m=30.0,
            rx_height_m=10.0,
            frequency_mhz=300.0,
            surface_refractivity_n0=301.0,
            earth_conductivity_sigma=0.005,
        )

    def test_p2p_algorithm_calls_validate_with_climate(self):
        source_path = "algorithm/p2p.py"
        with open(source_path, encoding="utf-8") as f:
            source = f.read()
        assert "climate=climate" in source
        assert "QgsProcessingException" in source



