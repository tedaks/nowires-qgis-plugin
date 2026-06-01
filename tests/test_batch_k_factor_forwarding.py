# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: batch itm_p2p_loss must forward k_factor parameter.

The v1.7.1 K-factor fix landed for P2P but was missing from the batch
_compute_single_link call to itm_p2p_loss. This test ensures k_factor is
explicitly forwarded.
"""

import os

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


def _source(name):
    with open(os.path.join(PLUGIN_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_batch_outputs_forwards_k_factor_to_itm():
    src = _source("batch/outputs.py")
    assert "k_factor=params.k_factor" in src, (
        "batch/outputs.py itm_p2p_loss call must forward k_factor=params.k_factor"
    )


def test_p2p_compute_forwards_k_factor_to_itm():
    src = _source("p2p/compute.py")
    assert "k_factor=p.k_factor" in src, (
        "p2p/compute.py itm_p2p_loss call must forward k_factor=p.k_factor"
    )