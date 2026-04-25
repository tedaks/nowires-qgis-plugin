# -*- coding: utf-8 -*-
"""Helpers for the Qt 6 / QGIS 4 UI APIs used by this plugin."""


def _resolve_qt6_enum(qt_namespace, scoped_enum_name, member_name):
    scoped_enum = getattr(qt_namespace, scoped_enum_name, None)
    if scoped_enum is not None and hasattr(scoped_enum, member_name):
        return getattr(scoped_enum, member_name)

    raise AttributeError(
        "Qt 6 enum lookup failed for Qt.{}.{}".format(scoped_enum_name, member_name)
    )


def widget_attribute_delete_on_close(qt_namespace):
    return _resolve_qt6_enum(qt_namespace, "WidgetAttribute", "WA_DeleteOnClose")


def dock_widget_area_right(qt_namespace):
    return _resolve_qt6_enum(qt_namespace, "DockWidgetArea", "RightDockWidgetArea")


def painter_blend_mode_color_dodge(qpainter_namespace):
    return _resolve_qt6_enum(
        qpainter_namespace, "CompositionMode", "CompositionMode_ColorDodge"
    )


def matplotlib_qt_backend():
    return ("QtAgg", "backend_qtagg")


def slider_orientation_horizontal(qt_namespace):
    return _resolve_qt6_enum(qt_namespace, "Orientation", "Horizontal")


def slider_tick_position_below(qt_namespace):
    return _resolve_qt6_enum(qt_namespace, "TickPosition", "TicksBelow")
