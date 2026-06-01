# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: K-factor preset label reflects v2.0.0 N0 coupling.

v1.7.0 shipped an interim label ("Fresnel Earth-radius factor (display only)")
clarifying the preset affected only Fresnel/LOS geometry. v2.0.0 supersedes
that: the preset is now coupled to a representative N0, so it DOES change the
ITM propagation prediction. The label must no longer claim "display only", and
the opt-in decouple control must be present for users who want the old
display-only behavior.
"""

import os


def _shared_params_source():
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "shared_params.py",
    )
    with open(source_path, encoding="utf-8") as f:
        return f.read()


def test_k_factor_label_no_longer_claims_display_only():
    """The preset now affects propagation; the v1.7.0 preset label must be gone."""
    source = _shared_params_source()
    assert "K_FACTOR_PRESET" in source
    assert "Fresnel Earth-radius factor (display only)" not in source, (
        "v2.0.0 couples the k-factor preset to N0; the interim v1.7.0 preset "
        "label claiming it is Fresnel-display-only must be removed"
    )
    assert "sets N0" in source, (
        "the preset label should signal that it now sets N0 (propagation)"
    )


def test_decouple_control_present_for_legacy_behavior():
    """A decouple option must exist so users can restore display-only behavior."""
    source = _shared_params_source()
    assert "DECOUPLE_N0" in source
    assert "Fresnel display only" in source, (
        "The decouple checkbox label should explain it makes the preset affect "
        "Fresnel display only (the pre-v2.0.0 behavior)"
    )
