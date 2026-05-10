# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
import math

from defaults import (
    DEFAULT_CABLE_LOSS_DB,
    DEFAULT_CLUTTER_PERCENTILE,
    DEFAULT_DOWNTILT_DEG,
    DEFAULT_EPSILON,
    DEFAULT_FREQ_MHZ,
    DEFAULT_FRONT_BACK_DB,
    DEFAULT_K_FACTOR,
    DEFAULT_LOCATION_PCT,
    DEFAULT_N0,
    DEFAULT_RADIUS_KM,
    DEFAULT_RX_GAIN_DBI,
    DEFAULT_RX_HEIGHT_M,
    DEFAULT_RX_SENSITIVITY_DBM,
    DEFAULT_SIGMA,
    DEFAULT_SITUATION_PCT,
    DEFAULT_STREET_WIDTH_M,
    DEFAULT_TIME_PCT,
    DEFAULT_TX_GAIN_DBI,
    DEFAULT_TX_HEIGHT_M,
    DEFAULT_TX_POWER_DBM,
)

from coverage_analysis_params import CoverageAnalysisParams
from p2p_analysis_params import P2PAnalysisParams
from batch_analysis_params import BatchAnalysisParams


class TestCoverageAnalysisParams:
    def test_construct_with_no_args(self):
        params = CoverageAnalysisParams()
        assert params.tx_lat == 0.0
        assert params.tx_lon == 0.0

    def test_defaults_match_defaults_module(self):
        params = CoverageAnalysisParams()
        assert params.tx_h == DEFAULT_TX_HEIGHT_M
        assert params.rx_h == DEFAULT_RX_HEIGHT_M
        assert params.f_mhz == DEFAULT_FREQ_MHZ
        assert params.radius_km == DEFAULT_RADIUS_KM
        assert params.time_pct == DEFAULT_TIME_PCT
        assert params.location_pct == DEFAULT_LOCATION_PCT
        assert params.situation_pct == DEFAULT_SITUATION_PCT
        assert params.tx_power == DEFAULT_TX_POWER_DBM
        assert params.tx_gain == DEFAULT_TX_GAIN_DBI
        assert params.rx_gain == DEFAULT_RX_GAIN_DBI
        assert params.cable_loss == DEFAULT_CABLE_LOSS_DB
        assert params.rx_sens == DEFAULT_RX_SENSITIVITY_DBM
        assert params.front_back_db == DEFAULT_FRONT_BACK_DB
        assert params.downtilt_deg == DEFAULT_DOWNTILT_DEG
        assert params.n0 == DEFAULT_N0
        assert params.epsilon == DEFAULT_EPSILON
        assert params.sigma == DEFAULT_SIGMA
        assert params.clutter_percentile == DEFAULT_CLUTTER_PERCENTILE
        assert params.street_width_m == DEFAULT_STREET_WIDTH_M

    def test_override_specific_fields(self):
        params = CoverageAnalysisParams(tx_h=50.0, f_mhz=900.0)
        assert params.tx_h == 50.0
        assert params.f_mhz == 900.0
        assert params.rx_h == DEFAULT_RX_HEIGHT_M
        assert params.radius_km == DEFAULT_RADIUS_KM

    def test_optional_fields_default_to_none(self):
        params = CoverageAnalysisParams()
        assert params.antenna_az is None
        assert params.antenna_bw_override is None
        assert params.clutter_grid is None
        assert params.tx_clutter_override is None
        assert params.rx_clutter_override is None
        assert params.cch_override_m is None

    def test_polarization_and_climate_defaults(self):
        params = CoverageAnalysisParams()
        assert params.polarization == 1
        assert params.climate == 1

    def test_clutter_disabled_by_default(self):
        params = CoverageAnalysisParams()
        assert params.clutter_enabled is False


class TestP2PAnalysisParams:
    _REQUIRED_KWARGS = dict(
        tx_lat=10.0,
        tx_lon=-80.0,
        rx_lat=10.5,
        rx_lon=-80.5,
        tx_h=30.0,
        rx_h=10.0,
        f_mhz=300.0,
        polarization=1,
        climate=1,
        time_pct=50.0,
        location_pct=50.0,
        situation_pct=50.0,
        tx_power=43.0,
        tx_gain=8.0,
        rx_gain=2.0,
        cable_loss=2.0,
        rx_sens=-100.0,
        k_factor=4.0 / 3.0,
        n0=301.0,
        epsilon=15.0,
        sigma=0.005,
    )

    def test_cannot_construct_with_no_args(self):
        try:
            P2PAnalysisParams()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass

    def test_construct_with_all_required_args(self):
        params = P2PAnalysisParams(**self._REQUIRED_KWARGS)
        assert params.tx_lat == 10.0
        assert params.rx_lon == -80.5

    def test_required_fields_are_first_21(self):
        import dataclasses
        fields = dataclasses.fields(P2PAnalysisParams)
        without_defaults = [f for f in fields if f.default is dataclasses.MISSING
                            and f.default_factory is dataclasses.MISSING]
        assert len(without_defaults) == 21

    def test_optional_defaults(self):
        params = P2PAnalysisParams(**self._REQUIRED_KWARGS)
        assert params.tx_antenna_config is None
        assert params.rx_antenna_config is None
        assert params.clutter_enabled is False
        assert params.clutter_model == "simple"
        assert params.clutter_percentile == DEFAULT_CLUTTER_PERCENTILE
        assert params.street_width_m == DEFAULT_STREET_WIDTH_M
        assert params.bel_enabled is False
        assert params.bel_building_type == "traditional"
        assert params.bel_elevation_angle_deg == 0.0

    def test_k_factor_required(self):
        params = P2PAnalysisParams(**self._REQUIRED_KWARGS)
        assert math.isclose(params.k_factor, DEFAULT_K_FACTOR, rel_tol=1e-9)

    def test_override_optional_field(self):
        params = P2PAnalysisParams(**self._REQUIRED_KWARGS, clutter_enabled=True)
        assert params.clutter_enabled is True


class TestBatchAnalysisParams:
    def test_construct_with_no_args(self):
        params = BatchAnalysisParams()
        assert params.mode == 0
        assert params.candidate_tx == []
        assert params.rx_points == []

    def test_defaults_match_defaults_module(self):
        params = BatchAnalysisParams()
        assert params.tx_h == DEFAULT_TX_HEIGHT_M
        assert params.rx_h == DEFAULT_RX_HEIGHT_M
        assert params.f_mhz == DEFAULT_FREQ_MHZ
        assert params.time_pct == DEFAULT_TIME_PCT
        assert params.location_pct == DEFAULT_LOCATION_PCT
        assert params.situation_pct == DEFAULT_SITUATION_PCT
        assert params.tx_power == DEFAULT_TX_POWER_DBM
        assert params.cable_loss == DEFAULT_CABLE_LOSS_DB
        assert params.rx_sens == DEFAULT_RX_SENSITIVITY_DBM
        assert params.n0 == DEFAULT_N0
        assert params.epsilon == DEFAULT_EPSILON
        assert params.sigma == DEFAULT_SIGMA
        assert params.clutter_percentile == DEFAULT_CLUTTER_PERCENTILE
        assert params.street_width_m == DEFAULT_STREET_WIDTH_M

    def test_k_factor_is_four_thirds(self):
        params = BatchAnalysisParams()
        assert math.isclose(params.k_factor, 4.0 / 3.0, rel_tol=1e-9)

    def test_k_factor_equals_default_k_factor(self):
        params = BatchAnalysisParams()
        assert math.isclose(params.k_factor, DEFAULT_K_FACTOR, rel_tol=1e-9)

    def test_polarization_and_climate_defaults(self):
        params = BatchAnalysisParams()
        assert params.polarization == 1
        assert params.climate == 1

    def test_gain_defaults(self):
        params = BatchAnalysisParams()
        assert params.tx_gain_default == DEFAULT_TX_GAIN_DBI
        assert params.rx_gain_default == DEFAULT_RX_GAIN_DBI

    def test_front_back_defaults(self):
        params = BatchAnalysisParams()
        assert params.tx_front_back_db == DEFAULT_FRONT_BACK_DB
        assert params.rx_front_back_db == DEFAULT_FRONT_BACK_DB

    def test_optional_fields_default_to_none(self):
        params = BatchAnalysisParams()
        assert params.tx_default_az is None
        assert params.rx_default_az is None
        assert params.clutter_grid is None
        assert params.tx_clutter_override is None
        assert params.rx_clutter_override is None
        assert params.cch_override_m is None
        assert params.elev is None

    def test_clutter_disabled_by_default(self):
        params = BatchAnalysisParams()
        assert params.clutter_enabled is False

    def test_default_preset_keys(self):
        params = BatchAnalysisParams()
        assert params.tx_default_preset_key == "omni"
        assert params.rx_default_preset_key == "omni"

    def test_override_specific_fields(self):
        params = BatchAnalysisParams(tx_h=50.0, f_mhz=900.0)
        assert params.tx_h == 50.0
        assert params.f_mhz == 900.0
        assert params.rx_h == DEFAULT_RX_HEIGHT_M