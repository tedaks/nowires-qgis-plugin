# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: all GPKG CreateLayer calls must use Z geometry types."""

import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN = os.path.join(_HERE, "..")

_FILES = [
    "p2p/outputs.py",
    "report/markers.py",
    "batch/writer.py",
    "contour/pipeline.py",
    "tile_merge.py",
]


def _read_module(name):
    with open(os.path.join(_PLUGIN, name), encoding="utf-8") as f:
        return f.read()


class TestGdalGeometryTypes:
    def test_p2p_outputs_uses_25d(self):
        source = _read_module("p2p/outputs.py")
        assert "wkbLineString25D" in source
        assert "wkbPolygon25D" in source
        assert "wkbLineString," not in source
        assert "wkbPolygon," not in source

    def test_markers_use_25d(self):
        source = _read_module("report/markers.py")
        assert "wkbPoint25D" in source
        assert "wkbPoint," not in source

    def test_batch_writer_uses_25d(self):
        source = _read_module("batch/writer.py")
        assert "wkbPoint25D" in source

    def test_contour_pipeline_uses_25d(self):
        source = _read_module("contour/pipeline.py")
        assert "wkbPolygon25D" in source

    def test_tile_merge_uses_25d(self):
        source = _read_module("tile_merge.py")
        assert "wkbPolygon25D" in source
