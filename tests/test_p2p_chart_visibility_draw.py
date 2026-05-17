# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for P2P profile chart bugs.

1. draw_idle after visibility toggle — checkbox toggles had no visible
   effect because update_visibility() never triggered a canvas repaint.
2. tx_marker/rx_marker NameError — markers were only created when
   len(los_h) > 0 but referenced unconditionally in the toggle loop.
3. _ChartCanvas.closeEvent dead code — cleanup was in a child widget's
   closeEvent that never fires; now connected via dock.destroyed signal.
4. setFloating before addDockWidget — setFloating has no effect before
   the dock is added to a QMainWindow.
"""
import inspect

from p2p_chart import show_profile_chart


def test_draw_idle_called_in_visibility_update():
    """fig.canvas.draw_idle() must be called inside update_visibility's
    deferred callback so checkbox toggles take effect immediately."""
    source = inspect.getsource(show_profile_chart)
    lines = source.splitlines()
    in_deferred = False
    found_draw_idle = False
    for line in lines:
        stripped = line.strip()
        if "def _a()" in stripped:
            in_deferred = True
        if in_deferred and "fig.canvas.draw_idle()" in stripped:
            found_draw_idle = True
            break
        if in_deferred and stripped.startswith("return"):
            break
    assert found_draw_idle, (
        "fig.canvas.draw_idle() must be called inside update_visibility's "
        "deferred callback after the artist-visibility loop"
    )


def test_markers_initialised_to_none():
    """tx_marker and rx_marker must be initialised to None so that
    update_visibility() does not raise NameError when los_h is empty."""
    source = inspect.getsource(show_profile_chart)
    assert "tx_marker, rx_marker = None, None" in source or (
        "tx_marker = None" in source and "rx_marker = None" in source
    ), "tx_marker and rx_marker must be initialised to None before conditional creation"


def test_toggle_loop_skips_none_markers():
    """The artist-visibility loop must skip None markers so toggling the
    Antennas checkbox does not raise NameError or AttributeError."""
    source = inspect.getsource(show_profile_chart)
    in_update = False
    loop_lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if "def update_visibility" in stripped:
            in_update = True
        if in_update:
            loop_lines.append(stripped)
            if "QTimer.singleShot" in stripped:
                break
    loop_text = "\n".join(loop_lines)
    assert "is not None" in loop_text, (
        "update_visibility must guard against None markers with "
        "`if art is not None` before calling set_visible"
    )


def test_dock_destroyed_signal_used_for_cleanup():
    """Tooltip disconnect and signal blocking must be connected to the dock
    via the destroyed signal, not in a child-widget closeEvent."""
    source = inspect.getsource(show_profile_chart)
    assert "dock.destroyed.connect" in source, (
        "Cleanup must be connected via dock.destroyed signal"
    )
    assert "class _ChartCanvas" not in source, (
        "_ChartCanvas class should be removed — its closeEvent was dead code"
    )


def test_add_dock_widget_before_set_floating():
    """addDockWidget must be called before setFloating for correct
    floating behavior on all platforms."""
    source = inspect.getsource(show_profile_chart)
    lines = source.splitlines()
    add_dock_line = None
    set_floating_line = None
    for i, line in enumerate(lines):
        if "addDockWidget" in line:
            add_dock_line = i
        if "setFloating" in line and "dock" in line:
            set_floating_line = i
    assert add_dock_line is not None, "addDockWidget call not found"
    assert set_floating_line is not None, "setFloating call not found"
    assert add_dock_line < set_floating_line, (
        f"addDockWidget (line {add_dock_line + 1}) must come before "
        f"setFloating (line {set_floating_line + 1})"
    )