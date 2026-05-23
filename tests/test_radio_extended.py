# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extended unit tests for radio.py — ITM bridge edge cases and validation."""

import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from NoWires.radio import (
    ITMResult,
    build_pfl,
    itm_p2p_loss,
    resolve_k_factor,
    validate_itm_input_ranges,
    ITM_MIN_SIGMA,
    K_FACTOR_PRESETS,
)


class TestValidateITMInputRangesConductivity:
    def test_accepts_sigma_at_minimum(self):
        validate_itm_input_ranges(
            tx_height_m=30.0,
            rx_height_m=10.0,
            frequency_mhz=300.0,
            surface_refractivity_n0=301.0,
            earth_conductivity_sigma=ITM_MIN_SIGMA,
        )

    def test_rejects_sigma_below_minimum(self):
        with pytest.raises(ValueError, match="conductivity sigma"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=10.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=1e-9,
            )

    def test_rejects_sigma_zero(self):
        with pytest.raises(ValueError, match="conductivity sigma"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=10.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=0.0,
            )

    def test_rejects_tx_height_below_min(self):
        with pytest.raises(ValueError, match="TX antenna height"):
            validate_itm_input_ranges(
                tx_height_m=0.1,
                rx_height_m=10.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=0.005,
            )

    def test_rejects_rx_height_above_max(self):
        with pytest.raises(ValueError, match="RX antenna height"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=5000.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=0.005,
            )

    def test_rejects_frequency_below_min(self):
        with pytest.raises(ValueError, match="Frequency"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=10.0,
                frequency_mhz=10.0,
                surface_refractivity_n0=301.0,
                earth_conductivity_sigma=0.005,
            )

    def test_rejects_n0_below_min(self):
        with pytest.raises(ValueError, match="Surface refractivity"):
            validate_itm_input_ranges(
                tx_height_m=30.0,
                rx_height_m=10.0,
                frequency_mhz=300.0,
                surface_refractivity_n0=100.0,
                earth_conductivity_sigma=0.005,
            )


class TestResolveKFactor:
    def test_has_preset_overrides_custom(self):
        result = resolve_k_factor(
            has_preset=True, has_custom=True, custom_value=1.5,
            preset_index=0, presets=K_FACTOR_PRESETS,
        )
        assert result == K_FACTOR_PRESETS[0]

    def test_no_preset_uses_custom(self):
        result = resolve_k_factor(
            has_preset=False, has_custom=True, custom_value=1.5,
            preset_index=2,
        )
        assert result == 1.5

    def test_no_preset_no_custom_uses_preset_default(self):
        result = resolve_k_factor(
            has_preset=False, has_custom=False, custom_value=None,
            preset_index=2,
        )
        assert result == K_FACTOR_PRESETS[2]


class TestBuildPFLEdgeCases:
    def test_single_point_elevations(self):
        pfl = build_pfl([100.0], 30.0)
        assert pfl[0] == 1.0
        assert pfl[1] == 30.0
        assert len(pfl) == 3

    def test_empty_elevations(self):
        pfl = build_pfl([], 30.0)
        assert pfl[0] == 1.0
        assert len(pfl) == 2 + 0  # empty list has length 0

    def test_large_step(self):
        elevs = [0.0, 100.0, 200.0, 300.0]
        pfl = build_pfl(elevs, 1000.0)
        assert pfl[0] == 3.0
        assert pfl[1] == 1000.0


class TestITMP2PLossExceptionHandling:
    def test_exception_returns_failed_result(self):
        profile = [1.0, 30.0, 100.0, 200.0]
        mock_climate = MagicMock()
        mock_polarization = MagicMock()
        mock_terrain = MagicMock()
        mock_predict = MagicMock(
            side_effect=RuntimeError("all-zero profile"),
        )
        with patch("NoWires.radio._get_itm", return_value=(
            mock_climate, mock_polarization, mock_terrain, mock_predict,
        )):
            result = itm_p2p_loss(
                h_tx__meter=30.0,
                h_rx__meter=10.0,
                profile=profile,
            )
            assert isinstance(result, ITMResult)
            assert result.failed is True

    def test_value_error_in_predict_p2p(self):
        profile = [1.0, 30.0, 100.0, 200.0]
        mock_climate = MagicMock()
        mock_polarization = MagicMock()
        mock_terrain = MagicMock()
        fake_result = MagicMock()
        fake_result.A__db = 0.0
        fake_result.intermediate = None
        fake_result.warnings = 0

        mock_predict = MagicMock(
            side_effect=ValueError("climate out of range"),
        )

        with patch("NoWires.radio._get_itm", return_value=(
            mock_climate, mock_polarization, mock_terrain, mock_predict,
        )):
            result = itm_p2p_loss(
                h_tx__meter=30.0,
                h_rx__meter=10.0,
                profile=profile,
            )
            assert result.failed is True
            assert math.isnan(result.loss_db)
            assert result.mode == -1
            assert result.warnings == 1

    def test_result_no_intermediate(self):
        profile = [1.0, 30.0, 100.0, 200.0]
        mock_climate = MagicMock()
        mock_polarization = MagicMock()
        mock_terrain = MagicMock()
        fake_result = MagicMock()
        fake_result.A__db = 145.0
        fake_result.intermediate = None
        fake_result.warnings = 0

        mock_predict = MagicMock(return_value=fake_result)

        with patch("NoWires.radio._get_itm", return_value=(
            mock_climate, mock_polarization, mock_terrain, mock_predict,
        )):
            result = itm_p2p_loss(
                h_tx__meter=30.0,
                h_rx__meter=10.0,
                profile=profile,
            )
            assert not result.failed
            assert result.loss_db == 145.0
            assert result.mode == 0
            assert result.warnings == 0
            assert result.d_hzn_tx_m == 0.0
            assert result.N_s == 0.0

    def test_result_with_intermediate_data(self):
        profile = [1.0, 30.0, 100.0, 200.0]
        mock_climate = MagicMock()
        mock_polarization = MagicMock()
        mock_terrain = MagicMock()
        fake_inter = MagicMock()
        fake_inter.d_hzn__meter = (500.0, 300.0)
        fake_inter.theta_hzn = (0.01, 0.02)
        fake_inter.h_e__meter = (50.0, 40.0)
        fake_inter.N_s = 301.0
        fake_inter.delta_h__meter = 25.0
        fake_inter.A_ref__db = 120.0
        fake_inter.A_fs__db = 100.0
        fake_inter.d__km = 5.0
        fake_inter.mode = 1

        fake_result = MagicMock()
        fake_result.A__db = 135.0
        fake_result.intermediate = fake_inter
        fake_result.warnings = 0

        mock_predict = MagicMock(return_value=fake_result)

        with patch("NoWires.radio._get_itm", return_value=(
            mock_climate, mock_polarization, mock_terrain, mock_predict,
        )):
            result = itm_p2p_loss(
                h_tx__meter=30.0,
                h_rx__meter=10.0,
                profile=profile,
            )
            assert not result.failed
            assert result.loss_db == 135.0
            assert result.mode == 1
            assert result.d_hzn_tx_m == 500.0
            assert result.d_hzn_rx_m == 300.0
            assert result.N_s == 301.0
            assert result.delta_h_m == 25.0
            assert result.A_ref_db == 120.0
            assert result.A_fs_db == 100.0
            assert result.d_km == 5.0

    def test_numpy_array_profile(self):
        profile = np.array([100.0, 110.0, 115.0, 108.0])
        mock_climate = MagicMock()
        mock_polarization = MagicMock()
        mock_terrain = MagicMock()
        fake_result = MagicMock()
        fake_result.A__db = 120.0
        fake_result.intermediate = None
        fake_result.warnings = 0

        mock_predict = MagicMock(return_value=fake_result)

        with patch("NoWires.radio._get_itm", return_value=(
            mock_climate, mock_polarization, mock_terrain, mock_predict,
        )):
            result = itm_p2p_loss(
                h_tx__meter=30.0,
                h_rx__meter=10.0,
                profile=profile,
            )
            assert not result.failed
            assert result.loss_db == 120.0

    def test_intermediate_mode_is_nan(self):
        profile = [1.0, 30.0, 100.0, 200.0]
        mock_climate = MagicMock()
        mock_polarization = MagicMock()
        mock_terrain = MagicMock()
        fake_inter = MagicMock()
        fake_inter.d_hzn__meter = (0.0, 0.0)
        fake_inter.theta_hzn = (0.0, 0.0)
        fake_inter.h_e__meter = (0.0, 0.0)
        fake_inter.N_s = 0.0
        fake_inter.delta_h__meter = 0.0
        fake_inter.A_ref__db = 0.0
        fake_inter.A_fs__db = 0.0
        fake_inter.d__km = 0.0
        fake_inter.mode = float("nan")

        fake_result = MagicMock()
        fake_result.A__db = 0.0
        fake_result.intermediate = fake_inter
        fake_result.warnings = 0

        mock_predict = MagicMock(return_value=fake_result)
        with patch("NoWires.radio._get_itm", return_value=(
            mock_climate, mock_polarization, mock_terrain, mock_predict,
        )):
            result = itm_p2p_loss(
                h_tx__meter=30.0,
                h_rx__meter=10.0,
                profile=profile,
            )
            assert result.mode == 0
