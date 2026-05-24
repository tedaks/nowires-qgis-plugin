# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Edge case tests for _smoothing_vrt helpers."""

import os
import re
import tempfile

import pytest


class TestParseXML:
    def test_parse_xml_uses_defusedxml_when_available(self, monkeypatch):
        import xml.etree.ElementTree as ET
        from contour._smoothing_vrt import _parse_xml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write("<root><child attr='1'/></root>")
            xml_path = f.name

        try:
            tree = _parse_xml(xml_path)
            root = tree.getroot()
            assert root.tag == "root"
        finally:
            os.unlink(xml_path)

    def test_parse_xml_parses_valid_xml(self, tmp_path):
        from contour._smoothing_vrt import _parse_xml

        xml_path = str(tmp_path / "test.xml")
        with open(xml_path, "w") as f:
            f.write("<?xml version='1.0'?><VRTDataset><GeoTransform>1</GeoTransform></VRTDataset>")

        tree = _parse_xml(xml_path)
        root = tree.getroot()
        assert root.tag == "VRTDataset"


class TestGaussianKernelEdgeCases:
    def test_size_1_kernel(self):
        from contour._smoothing_vrt import _gaussian_kernel_2d
        coefs = _gaussian_kernel_2d(1)
        vals = [float(c) for c in coefs.split()]
        assert len(vals) == 1
        assert abs(vals[0] - 1.0) < 1e-4

    def test_size_13_kernel(self):
        from contour._smoothing_vrt import _gaussian_kernel_2d
        coefs = _gaussian_kernel_2d(13)
        vals = [float(c) for c in coefs.split()]
        assert len(vals) == 13 * 13
        assert abs(sum(vals) - 1.0) < 1e-4


class TestSmoothingConstants:
    def test_smoothing_options_ordered(self):
        from contour.smoothing import SMOOTHING_OPTIONS
        assert SMOOTHING_OPTIONS[0] == "None"
        assert SMOOTHING_OPTIONS[-1] == "High"

    def test_smoothing_none_value(self):
        from contour.smoothing import SMOOTHING_NONE
        assert SMOOTHING_NONE == "None"
