# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import logging
import numpy as np


def test_bilinear_scalar_logs_debug_on_oob(caplog):
    from NoWires._bilinear import _bilinear_scalar
    gm = {"min_lat": 10.0, "max_lat": 20.0, "min_lon": 100.0, "max_lon": 110.0,
          "n_lat": 100, "n_lon": 100}
    data = np.zeros((100, 100), dtype=np.float32)
    with caplog.at_level(logging.DEBUG, logger="NoWires._bilinear"):
        result = _bilinear_scalar(data, gm, 0.0, 50.0)
    assert result != result
    assert any("out of bounds" in r.message.lower() for r in caplog.records)