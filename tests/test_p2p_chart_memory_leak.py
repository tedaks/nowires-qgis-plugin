# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later


def test_update_visibility_guarded_after_destruction():
    import contextlib
    import inspect
    from NoWires.p2p.chart import show_profile_chart
    src = inspect.getsource(show_profile_chart)
    assert "_destroyed" in src, (
        "_on_destroy must set _destroyed flag to guard stale closures"
    )
    assert "if _destroyed" in src, (
        "update_visibility must check _destroyed before manipulating figure"
    )

    assert "fig.clear()" in src, "_on_destroy must call fig.clear()"
    assert "plt.close(fig)" in src, "_on_destroy must call plt.close(fig)"