# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for separate percentage parameter defaults (v1.5.7 fix #12).

Before v1.5.7, coverage_params._add_pct_params used DEFAULT_TIME_PCT for
all three percentage parameters. The fix splits the loop so each addParameter
call references its own default constant.
"""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "radio_coverage/params.py"))


def test_add_pct_params_not_in_loop():
    """_add_pct_params must not use a loop with a single default value."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "for attr, label in" not in source or "DEFAULT_TIME_PCT" not in source.split("for attr")[0].split("_add_pct_params")[-1], (
        "_add_pct_params must not iterate over parameters with a single default; "
        "each must use its own constant"
    )


def test_add_pct_params_imports_all_three_defaults():
    """coverage_params must import DEFAULT_LOCATION_PCT and DEFAULT_SITUATION_PCT."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "DEFAULT_LOCATION_PCT" in source, (
        "coverage_params.py must import DEFAULT_LOCATION_PCT"
    )
    assert "DEFAULT_SITUATION_PCT" in source, (
        "coverage_params.py must import DEFAULT_SITUATION_PCT"
    )


def test_defaults_module_has_all_three():
    """defaults.py must define all three percentage constants."""
    from NoWires.defaults import (
        DEFAULT_TIME_PCT,
        DEFAULT_LOCATION_PCT,
        DEFAULT_SITUATION_PCT,
    )
    assert DEFAULT_TIME_PCT == 50.0
    assert DEFAULT_LOCATION_PCT == 50.0
    assert DEFAULT_SITUATION_PCT == 50.0