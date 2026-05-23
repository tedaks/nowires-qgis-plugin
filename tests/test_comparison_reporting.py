# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for comparison_reporting: build_panel_info and build_delta_info."""


import numpy as np
import pytest

from comparison.reporting import build_panel_info, build_delta_info, validate_panels, resolve_output_paths


@pytest.mark.qgis_integration
class TestValidatePanels:
    def test_co_located_positions_pass(self):
        from qgis.core import QgsPointXY
        a = QgsPointXY(121.0, 14.5)
        b = QgsPointXY(121.0, 14.5)
        validate_panels(a, b, 5.0, 5.0)

    def test_tx_positions_differ_beyond_tolerance_raises(self):
        from qgis.core import QgsPointXY, QgsProcessingException
        a = QgsPointXY(121.0, 14.5)
        b = QgsPointXY(121.0005, 14.5)  # 5e-4 > 1e-4 tolerance
        with pytest.raises(QgsProcessingException, match="TX positions differ"):
            validate_panels(a, b, 5.0, 5.0)

    def test_tx_positions_within_tolerance_pass(self):
        from qgis.core import QgsPointXY
        a = QgsPointXY(121.0, 14.5)
        b = QgsPointXY(121.0 + 5e-5, 14.5)  # 5e-5 < 1e-4 tolerance
        validate_panels(a, b, 5.0, 5.0)


class TestResolveOutputPaths:
    def test_asserts_tmpdir_not_none(self):
        class FakeTmpMgr:
            def make_dir(self, name, persistent=False):
                return None
        with pytest.raises(AssertionError):
            resolve_output_paths(
                None, None, None, None, None, FakeTmpMgr())

    def test_output_dir_provides_all_paths(self):
        import os
        import tempfile
        class FakeTmpMgr:
            def make_dir(self, name, persistent=False):
                return "/unused"
        with tempfile.TemporaryDirectory() as tmpdir:
            out_a, out_b, out_d = os.path.join(tmpdir, "a.tif"), os.path.join(tmpdir, "b.tif"), os.path.join(tmpdir, "d.tif")
            ra, rb, rd, _, _ = resolve_output_paths(
                tmpdir, out_a, out_b, out_d, None, FakeTmpMgr())
            assert ra == out_a
            assert rb == out_b
            assert rd == out_d
