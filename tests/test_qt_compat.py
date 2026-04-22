# -*- coding: utf-8 -*-
"""Unit tests for QGIS 4 Qt helpers and plugin metadata."""

import configparser
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qt_compat import (
    dock_widget_area_right,
    matplotlib_qt_backend,
    painter_blend_mode_color_dodge,
    widget_attribute_delete_on_close,
)


PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..")


class _QtLegacyFlat:
    WA_DeleteOnClose = "wa-delete"
    RightDockWidgetArea = "right-dock"


class _Qt6Like:
    class WidgetAttribute:
        WA_DeleteOnClose = "wa-delete"

    class DockWidgetArea:
        RightDockWidgetArea = "right-dock"


class _PainterLegacyFlat:
    CompositionMode_ColorDodge = "color-dodge"


class _PainterQt6Like:
    class CompositionMode:
        CompositionMode_ColorDodge = "color-dodge"


def test_widget_attribute_delete_on_close_uses_qt6_enum_namespace():
    assert widget_attribute_delete_on_close(_Qt6Like) == "wa-delete"


def test_widget_attribute_delete_on_close_rejects_legacy_flat_qt_style():
    with pytest.raises(AttributeError, match="WidgetAttribute"):
        widget_attribute_delete_on_close(_QtLegacyFlat)


def test_dock_widget_area_right_uses_qt6_enum_namespace():
    assert dock_widget_area_right(_Qt6Like) == "right-dock"


def test_dock_widget_area_right_rejects_legacy_flat_qt_style():
    with pytest.raises(AttributeError, match="DockWidgetArea"):
        dock_widget_area_right(_QtLegacyFlat)


def test_matplotlib_qt_backend_is_fixed_for_qgis4():
    assert matplotlib_qt_backend() == ("QtAgg", "backend_qtagg")


def test_painter_blend_mode_color_dodge_uses_qt6_enum_namespace():
    assert painter_blend_mode_color_dodge(_PainterQt6Like) == "color-dodge"


def test_painter_blend_mode_color_dodge_rejects_legacy_flat_qt_style():
    with pytest.raises(AttributeError, match="CompositionMode"):
        painter_blend_mode_color_dodge(_PainterLegacyFlat)


def test_metadata_targets_qgis4_only():
    parser = configparser.ConfigParser()
    parser.read(os.path.join(PLUGIN_DIR, "metadata.txt"))
    assert parser["general"]["qgisMinimumVersion"].startswith("4")
