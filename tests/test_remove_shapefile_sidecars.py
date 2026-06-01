# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Test _remove_shapefile_sidecars from report/markers.py."""

import os
from NoWires.report.markers import _remove_shapefile_sidecars


def test_removes_existing_shp_sidecar_files(tmp_path):
    base = str(tmp_path / "test.shp")
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        open(base.replace(".shp", ext) if ext != ".shp" else base, "w").close()
    _remove_shapefile_sidecars(base)
    assert os.path.exists(base.replace(".shp", ".shp"))  # .shp NOT removed
    for ext in (".shx", ".dbf", ".prj"):
        assert not os.path.exists(base.replace(".shp", ext))


def test_no_error_on_nonexistent_sidecars(tmp_path):
    base = str(tmp_path / "nonexistent.shp")
    _remove_shapefile_sidecars(base)
