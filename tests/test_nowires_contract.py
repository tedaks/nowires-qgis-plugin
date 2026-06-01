# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Contract tests for the nowires plugin module.

Tests structural invariants that don't require a QGIS runtime.
"""

import os


class TestNowiresModuleContract:
    def test_file_has_spdx_identifier(self):
        src_dir = os.path.dirname(__file__)
        path = os.path.join(src_dir, "..", "nowires.py")
        with open(path, "r") as f:
            content = f.read()
        assert "SPDX-License-Identifier: MIT" in content

    def test_class_factory_is_exported(self):
        src_dir = os.path.dirname(__file__)
        path = os.path.join(src_dir, "..", "nowires.py")
        with open(path, "r") as f:
            content = f.read()
        assert "class NoWiresPlugin" in content
        assert "classFactory" in content or "def classFactory" in open(
            os.path.join(src_dir, "..", "__init__.py")
        ).read()

    def test_stale_temp_dir_count_function_exists(self):
        src_dir = os.path.dirname(__file__)
        path = os.path.join(src_dir, "..", "nowires.py")
        with open(path, "r") as f:
            content = f.read()
        assert "def _stale_temp_dir_count" in content

    def test_stale_temp_dir_count_signature(self):
        src_dir = os.path.dirname(__file__)
        path = os.path.join(src_dir, "..", "nowires.py")
        with open(path, "r") as f:
            content = f.read()
        assert "def _stale_temp_dir_count(max_entries" in content

    def test_menu_name_constant(self):
        src_dir = os.path.dirname(__file__)
        path = os.path.join(src_dir, "..", "nowires.py")
        with open(path, "r") as f:
            content = f.read()
        assert "_MENU_NAME" in content