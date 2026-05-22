# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later


def test_show_profile_chart_returns_none_in_headless():
    import inspect
    from NoWires.p2p.chart import show_profile_chart
    src = inspect.getsource(show_profile_chart)
    assert "qgis.utils.iface is None" in src, (
        "show_profile_chart must check for headless QGIS (iface is None)"
    )