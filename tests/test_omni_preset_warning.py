# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests: omni-preset silent-snap helper emits feedback when needed."""

from unittest.mock import MagicMock

from NoWires.shared_params import warn_if_omni_preset_discards_directional


def test_omni_preset_helper_emits_warning():
    """preset=Omni with non-default BW or downtilt must pushInfo."""
    feedback = MagicMock()
    warn_if_omni_preset_discards_directional(
        feedback, antenna_preset=0, antenna_bw_override=90.0, downtilt_deg=5.0)
    assert feedback.pushInfo.called


def test_omni_preset_helper_silent_at_defaults():
    """preset=Omni at omnidirectional defaults must NOT pushInfo."""
    feedback = MagicMock()
    warn_if_omni_preset_discards_directional(
        feedback, antenna_preset=0, antenna_bw_override=360.0, downtilt_deg=0.0)
    assert not feedback.pushInfo.called


def test_omni_preset_helper_silent_for_other_presets():
    """preset != Omni must NOT pushInfo even with directional values set."""
    feedback = MagicMock()
    warn_if_omni_preset_discards_directional(
        feedback, antenna_preset=1, antenna_bw_override=90.0, downtilt_deg=5.0)
    assert not feedback.pushInfo.called


def test_omni_preset_helper_silent_when_feedback_none():
    """No feedback object must not raise."""
    warn_if_omni_preset_discards_directional(
        None, antenna_preset=0, antenna_bw_override=90.0, downtilt_deg=5.0)


def test_omni_preset_helper_treats_none_bw_as_omni_default():
    """antenna_bw_override=None means omni default (360); should be silent."""
    feedback = MagicMock()
    warn_if_omni_preset_discards_directional(
        feedback, antenna_preset=0, antenna_bw_override=None, downtilt_deg=0.0)
    assert not feedback.pushInfo.called


def test_omni_preset_helper_fires_on_nonzero_downtilt_alone():
    """preset=Omni with default BW but nonzero downtilt must still warn."""
    feedback = MagicMock()
    warn_if_omni_preset_discards_directional(
        feedback, antenna_preset=0, antenna_bw_override=360.0, downtilt_deg=3.0)
    assert feedback.pushInfo.called
