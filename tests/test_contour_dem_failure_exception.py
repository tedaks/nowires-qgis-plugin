# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test: DEM download/merge failure must raise QgsProcessingException.

Before v1.6.1, the contour algorithm silently returned {} on DEM failure,
hiding the error from the user. The fix raises QgsProcessingException instead.
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.join(_HERE, os.pardir)
_SOURCE_FILE = os.path.normpath(os.path.join(_PLUGIN_DIR, "algorithm/contour.py"))


def test_dem_failure_raises_qgsprocessingexception_not_return_empty():
    """Source-level contract: after DEM None check, raise QgsProcessingException, not return {}."""
    with open(_SOURCE_FILE) as f:
        source = f.read()
    assert 'raise QgsProcessingException(\n                    "DEM download/merge failed for the selected area.")' in source or \
           'raise QgsProcessingException("DEM download/merge failed for the selected area.")' in source or \
           'raise QgsProcessingException(\n                "DEM download/merge failed for the selected area.")' in source, (
        "algorithm/contour.py must raise QgsProcessingException when DEM download/merge fails"
    )


def test_dem_failure_no_silent_return():
    """Regression: no silent return {} immediately after the DEM None check."""
    with open(_SOURCE_FILE) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if "merged_path is None" in line:
            for j in range(i + 1, min(i + 4, len(lines))):
                if "return {}" in lines[j]:
                    assert False, (
                        "return {} found after merged_path is None check; "
                        "should raise QgsProcessingException instead"
                    )
            break