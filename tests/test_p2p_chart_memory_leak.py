# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later


def test_on_destroy_clears_and_closes_figure():
    import inspect
    from NoWires.p2p.chart import show_profile_chart
    src = inspect.getsource(show_profile_chart)
    assert "fig.clear()" in src, "_on_destroy must call fig.clear()"
    assert "plt.close(fig)" in src, "_on_destroy must call plt.close(fig)"