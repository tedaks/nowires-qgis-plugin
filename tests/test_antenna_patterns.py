# -*- coding: utf-8 -*-
"""Behavioral tests for antenna presets, pattern files, and vertical downtilt."""

import pytest

from antenna import (
    ANTENNA_PRESETS,
    AntennaConfig,
    antenna_gain_factor,
    antenna_gain_adjustment_db,
)


def test_existing_antenna_gain_factor_still_supports_omni_and_sector():
    assert antenna_gain_factor(90.0, None, 360.0) == 0.0
    assert antenna_gain_factor(45.0, 0.0, 90.0) == pytest.approx(-3.0, abs=0.01)
    assert antenna_gain_factor(180.0, 0.0, 90.0, front_back_db=30.0) == -30.0


def test_presets_define_expected_shape_defaults():
    assert ANTENNA_PRESETS["omni"].horizontal_beamwidth_deg == 360.0
    assert ANTENNA_PRESETS["sector_90"].horizontal_beamwidth_deg == 90.0
    assert ANTENNA_PRESETS["sector_120"].front_back_db == 25.0
    assert ANTENNA_PRESETS["dish_20"].horizontal_beamwidth_deg == 20.0


def test_antenna_gain_adjustment_combines_horizontal_and_vertical_terms():
    config = AntennaConfig(
        preset="sector_90",
        azimuth_deg=0.0,
        horizontal_beamwidth_deg=90.0,
        vertical_beamwidth_deg=10.0,
        front_back_db=25.0,
        downtilt_deg=5.0,
    )

    assert antenna_gain_adjustment_db(
        bearing_deg=0.0,
        elevation_angle_deg=-5.0,
        config=config,
    ) == pytest.approx(0.0, abs=0.001)

    assert antenna_gain_adjustment_db(
        bearing_deg=180.0,
        elevation_angle_deg=-5.0,
        config=config,
    ) == pytest.approx(-25.0, abs=0.001)

    assert antenna_gain_adjustment_db(
        bearing_deg=0.0,
        elevation_angle_deg=0.0,
        config=config,
    ) == pytest.approx(-3.0, abs=0.001)


def test_pattern_file_interpolates_relative_adjustment(tmp_path):
    from pathlib import Path

    path = tmp_path / "horizontal.csv"
    path.write_text("angle_deg,gain_adjust_db\n0,0\n90,-12\n180,-30\n270,-12\n360,0\n")

    config = AntennaConfig(
        preset="custom",
        azimuth_deg=0.0,
        horizontal_pattern_path=str(path),
        front_back_db=30.0,
    )

    assert antenna_gain_adjustment_db(45.0, 0.0, config) == pytest.approx(-6.0)
    assert antenna_gain_adjustment_db(180.0, 0.0, config) == pytest.approx(-30.0)