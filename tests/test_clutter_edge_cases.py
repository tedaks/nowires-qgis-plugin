# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.

"""Edge-case coverage tests for missed lines in clutter modules.

Targets:
  clutter/p2108_height_gain.py  — lines 86 (R<=0 guard), 106 (vec clamp log)
  clutter/p2109_bel.py          — lines 58 (scalar clamp log),
                                   98 (vec clamp log), 115 (np.maximum)
  clutter/p2108_common.py       — lines 23 (_ndtr), 37, 39 (_ndtri extremes)
  clutter/context.py            — line 51 (unknown-model ValueError)
  clutter/p2108_terrestrial_stat.py — line 88 (vec clamp log)
"""

import logging

import numpy as np
import pytest

from clutter.p2108_common import (
    _ndtr,
    _ndtri,
    f_inv_normal,
    validate_frequency_ghz,
)
from clutter.p2108_height_gain import (
    height_gain_loss,
    height_gain_loss_vec,
)
from clutter.p2109_bel import (
    building_entry_loss,
    building_entry_loss_vec,
)
from clutter.p2108_terrestrial_stat import (
    clutter_loss_p2108_terrestrial_stat_vec,
)
from NoWires.clutter.context import build_initial_clutter_context

_HG_LOGGER = "NoWires.clutter.p2108_height_gain"
_BEL_LOGGER = "NoWires.clutter.p2109_bel"
_TS_LOGGER = "NoWires.clutter.p2108_terrestrial_stat"


# ---------------------------------------------------------------------------
# p2108_height_gain — line 86 R<=0 guard
# ---------------------------------------------------------------------------

def test_height_gain_loss_R_le_zero(monkeypatch, caplog):
    """height_gain_loss returns 0 when R <= 0 (line 86)."""
    import clutter.p2108_height_gain as mod

    monkeypatch.setattr(mod, "_MIN_HEIGHT_M", -100.0)
    monkeypatch.setitem(
        mod._CATEGORY_PARAMS, "zero_r_cat",
        {"R_m": 0, "method": "2b"},
    )
    caplog.set_level(logging.INFO, logger=_HG_LOGGER)
    result = height_gain_loss(h_m=-50.0, f_ghz=1.0, category="zero_r_cat")
    assert result == 0.0


# ---------------------------------------------------------------------------
# p2108_height_gain — freq clamping log paths (scalar + vector)
# ---------------------------------------------------------------------------

def test_height_gain_loss_freq_clamped_log(caplog):
    """Scalar height_gain_loss clamps f > 3 GHz and logs (line 69 path)."""
    caplog.set_level(logging.INFO, logger=_HG_LOGGER)
    result = height_gain_loss(h_m=5.0, f_ghz=5.0, category="urban")
    assert result > 0.0
    assert "clamped" in caplog.text


def test_height_gain_loss_vec_freq_clamped_log(caplog):
    """Vector height_gain_loss_vec clamps f > 3 GHz and logs (line 106)."""
    caplog.set_level(logging.INFO, logger=_HG_LOGGER)
    result = height_gain_loss_vec(
        h_m_arr=[2.0, 5.0], f_ghz=5.0,
        categories=["urban", "open_rural"],
    )
    assert np.all(result >= 0.0)
    assert "clamped" in caplog.text


# ---------------------------------------------------------------------------
# p2109_bel — scalar freq clamping log (line 58)
# ---------------------------------------------------------------------------

def test_building_entry_loss_freq_clamped(caplog):
    """Scalar BEL clamps f > 100 GHz and logs (line 58)."""
    caplog.set_level(logging.INFO, logger=_BEL_LOGGER)
    result = building_entry_loss(f_ghz=200.0, building_type="traditional",
                                 theta_deg=0.0, p=50.0)
    assert result >= 0.0
    assert "clamped" in caplog.text


# ---------------------------------------------------------------------------
# p2109_bel — vector freq clamping log (line 98)
# ---------------------------------------------------------------------------

def test_building_entry_loss_vec_freq_clamped(caplog):
    """Vector BEL clamps f > 100 GHz and logs (line 98)."""
    caplog.set_level(logging.INFO, logger=_BEL_LOGGER)
    result = building_entry_loss_vec(
        f_ghz_arr=[200.0, 300.0],
        building_type="traditional", theta_deg=0.0, p=50.0,
    )
    assert np.all(result >= 0.0)
    assert "clamped" in caplog.text


# ---------------------------------------------------------------------------
# p2109_bel — np.maximum(0.0, L_BEL) path (line 115)
# ---------------------------------------------------------------------------

def test_building_entry_loss_vec_np_maximum_clamp():
    """Vector BEL returns 0 when L_BEL is negative (line 115)."""
    result = building_entry_loss_vec(
        f_ghz_arr=[0.08],
        building_type="traditional",
        theta_deg=0.0,
        p=0.01,
    )
    assert result[0] == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# p2108_common — validate_frequency_ghz with P.2109 bounds (lines 84-88)
# ---------------------------------------------------------------------------

def test_validate_frequency_ghz_below_min():
    """Clamp to min when f < min_ghz (P.2109 bound: 0.08 GHz)."""
    f, clamped = validate_frequency_ghz(0.01, 0.08, 100.0)
    assert f == 0.08
    assert clamped is True


def test_validate_frequency_ghz_above_max():
    """Clamp to max when f > max_ghz (P.2109 bound: 100 GHz)."""
    f, clamped = validate_frequency_ghz(200.0, 0.08, 100.0)
    assert f == 100.0
    assert clamped is True


# ---------------------------------------------------------------------------
# p2108_common — f_inv_normal boundary percentiles (lines 77-78 path)
# ---------------------------------------------------------------------------

def test_f_inv_normal_extreme_low_percentile():
    """f_inv_normal at p=0.01 should be strongly negative."""
    val = f_inv_normal(0.01)
    assert val < -3.0


def test_f_inv_normal_extreme_high_percentile():
    """f_inv_normal at p=99.99 should be strongly positive."""
    val = f_inv_normal(99.99)
    assert val > 3.0


# ---------------------------------------------------------------------------
# p2108_common — _ndtr body (line 23) and _ndtri extremes (lines 37, 39)
# ---------------------------------------------------------------------------

def test_ndtr_body_coverage():
    """Direct call to _ndtr to cover line 23."""
    assert _ndtr(0.0) == pytest.approx(0.5, abs=1e-10)
    assert _ndtr(3.0) == pytest.approx(0.99865, abs=0.0001)


def test_ndtri_p_le_zero():
    """_ndtri returns -inf when p <= 0 (line 37)."""
    assert _ndtri(0.0) == float("-inf")
    assert _ndtri(-0.5) == float("-inf")


def test_ndtri_p_ge_one():
    """_ndtri returns +inf when p >= 1 (line 39)."""
    assert _ndtri(1.0) == float("inf")
    assert _ndtri(2.0) == float("inf")


# ---------------------------------------------------------------------------
# clutter/context — build_initial_clutter_context unknown model (line 51)
# ---------------------------------------------------------------------------

def test_build_initial_clutter_context_unknown_model_raises():
    """build_initial_clutter_context with invalid model raises ValueError."""
    with pytest.raises(ValueError, match="ClutterLossContext\\.model must be one of"):
        build_initial_clutter_context(
            frequency_mhz=900.0,
            tx_height_m=30.0,
            rx_height_m=2.0,
            tx_ground_elevation_m=250.0,
            polarization=0,
            cch_override_m=None,
            model="nonexistent",
            percentile=50.0,
            street_width_m=27.0,
            bel_enabled=False,
            bel_building_type="traditional",
            bel_elevation_angle_deg=0.0,
        )


# ---------------------------------------------------------------------------
# p2108_terrestrial_stat — vec freq clamping log (line 88)
# ---------------------------------------------------------------------------

def test_clutter_loss_terrestrial_stat_vec_freq_clamped(caplog):
    """Vector terrestrial clutter loss clamps f < 0.5 GHz and logs (line 88)."""
    caplog.set_level(logging.INFO, logger=_TS_LOGGER)
    result = clutter_loss_p2108_terrestrial_stat_vec(
        d_km_arr=[1.0, 5.0], f_ghz=0.03, p=50.0,
    )
    assert np.all(result >= 0.0)
    assert "clamped" in caplog.text
