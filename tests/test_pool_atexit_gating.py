# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for atexit re-registration gating (v1.5.7 fix #7).

Source-level contract test: _init_cov_pool must gate the atexit registration
with a module-level flag so that re-initialization does not accumulate handlers.
"""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "coverage_pool.py"))


def test_atexit_gated_by_module_flag():
    """The atexit.register call must be guarded by _cov_pool_atexit_registered."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert "_cov_pool_atexit_registered" in source, (
        "coverage_pool.py must define a module-level _cov_pool_atexit_registered flag"
    )
    assert "if not _cov_pool_atexit_registered:" in source, (
        "_init_cov_pool must gate atexit.register with _cov_pool_atexit_registered"
    )


def test_atexit_registered_flag_exists():
    """The module must export _cov_pool_atexit_registered."""
    from coverage_pool import _cov_pool_atexit_registered
    assert isinstance(_cov_pool_atexit_registered, bool)