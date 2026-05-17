# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
import math

from constants import (
    BYTES_PER_MEBIBYTE,
    CLIMATE_NAMES,
    COVERAGE_NODATA,
    DEFAULT_PROFILE_STEP_M,
    DEGREE_PADDING,
    EARTH_RADIUS_M,
    GRID_SIZE_OPTIONS,
    GRID_SIZE_PRESETS,
    ITM_LOSS_UPPER_BOUND,
    K_FACTOR_PRESETS_OPTIONS,
    MAX_AOI_EXTENT_DEGREES,
    METERS_PER_DEGREE_LAT,
    FEET_PER_METER,
    FRESNEL_60PCT_FACTOR,
    POLARIZATION_NAMES,
)
from defaults import (
    DEFAULT_ANTENNA_AZIMUTH,
    DEFAULT_ANTENNA_BEAMWIDTH,
    DEFAULT_CABLE_LOSS_DB,
    DEFAULT_CLUTTER_PERCENTILE,
    DEFAULT_DOWNTILT_DEG,
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
    DEFAULT_EPSILON,
)


def test_earth_radius_reasonable():
    assert 6_370_000 <= EARTH_RADIUS_M <= 6_372_000


def test_meters_per_degree_lat_reasonable():
    assert 110_000 <= METERS_PER_DEGREE_LAT <= 112_000


def test_feet_per_meter_greater_than_one():
    assert FEET_PER_METER > 1.0


def test_bytes_per_mebibyte():
    assert BYTES_PER_MEBIBYTE == 1024 * 1024


def test_default_profile_step_positive():
    assert DEFAULT_PROFILE_STEP_M > 0


def test_degree_padding_positive():
    assert DEGREE_PADDING > 0


def test_max_aoi_extent_positive():
    assert MAX_AOI_EXTENT_DEGREES > 0


def test_polarization_names_keys():
    assert set(POLARIZATION_NAMES.keys()) == {0, 1}


def test_polarization_names_values_distinct():
    values = list(POLARIZATION_NAMES.values())
    assert len(values) == len(set(values))


def test_climate_names_keys_zero_through_six():
    assert set(CLIMATE_NAMES.keys()) == set(range(7))


def test_climate_names_values_distinct():
    values = list(CLIMATE_NAMES.values())
    assert len(values) == len(set(values))


def test_grid_size_presets_length_matches_options():
    assert len(GRID_SIZE_PRESETS) == len(GRID_SIZE_OPTIONS)


def test_grid_size_presets_match_options_numeric_part():
    for preset, option in zip(GRID_SIZE_PRESETS, GRID_SIZE_OPTIONS):
        numeric = option.split()[0]
        assert str(preset) == numeric


def test_k_factor_presets_options_count():
    assert len(K_FACTOR_PRESETS_OPTIONS) == 6


def test_k_factor_presets_standard_atmosphere():
    assert "1.33" in K_FACTOR_PRESETS_OPTIONS[2]
    assert "Standard atmosphere" in K_FACTOR_PRESETS_OPTIONS[2]


def test_coverage_nodata_negative():
    assert COVERAGE_NODATA < 0


def test_default_k_factor_approx():
    assert math.isclose(DEFAULT_K_FACTOR, 4.0 / 3.0, rel_tol=1e-9)


def test_default_k_factor_value():
    assert abs(DEFAULT_K_FACTOR - 1.333333333) < 0.001


def test_fresnel_60_pct_factor():
    assert FRESNEL_60PCT_FACTOR == 0.6


def test_default_tx_height():
    assert DEFAULT_TX_HEIGHT_M == 30.0


def test_default_rx_height():
    assert DEFAULT_RX_HEIGHT_M == 10.0


def test_default_freq_mhz():
    assert DEFAULT_FREQ_MHZ == 300.0


def test_default_radius_km():
    assert DEFAULT_RADIUS_KM == 50.0


def test_default_tx_power():
    assert DEFAULT_TX_POWER_DBM == 43.0


def test_default_tx_gain():
    assert DEFAULT_TX_GAIN_DBI == 8.0


def test_default_rx_gain():
    assert DEFAULT_RX_GAIN_DBI == 2.0


def test_default_cable_loss():
    assert DEFAULT_CABLE_LOSS_DB == 2.0


def test_default_rx_sensitivity():
    assert DEFAULT_RX_SENSITIVITY_DBM == -100.0


def test_default_front_back():
    assert DEFAULT_FRONT_BACK_DB == 25.0


def test_default_time_pct():
    assert DEFAULT_TIME_PCT == 50.0


def test_default_location_pct():
    assert DEFAULT_LOCATION_PCT == 50.0


def test_default_situation_pct():
    assert DEFAULT_SITUATION_PCT == 50.0


def test_default_n0():
    assert DEFAULT_N0 == 301.0


def test_default_epsilon():
    assert DEFAULT_EPSILON == 15.0


def test_default_sigma():
    assert DEFAULT_SIGMA == 0.005


def test_default_antenna_azimuth():
    assert DEFAULT_ANTENNA_AZIMUTH == 0.0


def test_default_antenna_beamwidth():
    assert DEFAULT_ANTENNA_BEAMWIDTH == 360.0


def test_default_downtilt():
    assert DEFAULT_DOWNTILT_DEG == 0.0


def test_default_clutter_percentile():
    assert DEFAULT_CLUTTER_PERCENTILE == 50.0


def test_default_street_width():
    assert DEFAULT_STREET_WIDTH_M == 27.0


def test_k_factor_cross_reference_with_presets():
    assert "1.33" in K_FACTOR_PRESETS_OPTIONS[2]
    assert math.isclose(DEFAULT_K_FACTOR, 4.0 / 3.0, rel_tol=1e-9)


def test_itm_loss_upper_bound_is_400():
    assert ITM_LOSS_UPPER_BOUND == 400.0


def test_itm_loss_upper_bound_is_numeric():
    assert isinstance(ITM_LOSS_UPPER_BOUND, float)