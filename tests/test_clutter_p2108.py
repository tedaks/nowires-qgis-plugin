# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.

import warnings

import numpy as np
import pytest

from clutter_p2108 import clutter_loss_p2108, clutter_loss_p2108_vec


def test_shim_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        clutter_loss_p2108(1000.0, "urban", 1000.0)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()


def test_open_category_returns_zero():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert clutter_loss_p2108(1000.0, "open", 1000.0) == 0.0


def test_delegated_to_terrestrial_stat():
    from p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        v = clutter_loss_p2108(1000.0, "urban", 1000.0)
    expected = clutter_loss_p2108_terrestrial_stat(1.0, 1.0, p=50.0)
    assert v == pytest.approx(expected, abs=0.01)


def test_vectorized_delegates():
    from p2108_terrestrial_stat import clutter_loss_p2108_terrestrial_stat_vec
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        vec = clutter_loss_p2108_vec(np.array([500.0, 1000.0]), "suburban", 2000.0)
    expected = clutter_loss_p2108_terrestrial_stat_vec(
        np.array([0.5, 1.0]), 2.0, p=50.0)
    np.testing.assert_allclose(vec, expected, atol=0.01)


def test_loss_is_non_negative():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for cat in ["open_rural", "dense_rural", "suburban", "urban"]:
            for d in [100.0, 1000.0, 10000.0]:
                assert clutter_loss_p2108(d, cat, 1000.0) >= 0.0