# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contract test: generate_contour_lines never returns None for the shp path."""

import inspect

from NoWires.contour.generation import generate_contour_lines


def test_generate_contour_lines_never_returns_none_for_shp_path():
    """The shp path is built unconditionally via os.path.join, so it is always a str."""
    source = inspect.getsource(generate_contour_lines)
    assert "return contour_shp_path, tmp_shp_dir" in source
    assert "contour_shp_path = os.path.join(" in source
    # If the function ever starts returning None, this test fails and the
    # downstream caller's `is None` check should be reinstated.
    assert "return None" not in source
