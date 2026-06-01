# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test: project-relative output path helper exists and works."""

import os
from unittest.mock import MagicMock

from NoWires.algorithm._project_paths import _project_or_temp_dir


def test_no_project_falls_back_to_tmp():
    """Unsaved project returns a temp directory."""
    context = MagicMock()
    context.project.return_value = None
    tmp_mgr = MagicMock()
    tmp_mgr.make_dir.return_value = "/tmp/nowires_test"

    result = _project_or_temp_dir(tmp_mgr, context, None, "test_subdir")
    assert result == "/tmp/nowires_test"
    tmp_mgr.make_dir.assert_called_once_with("test_subdir", persistent=True)
    tmp_mgr.warn_persistent.assert_called_once_with(None)


def test_empty_project_file_falls_back_to_tmp():
    """Project with no fileName returns a temp directory."""
    context = MagicMock()
    context.project().fileName.return_value = ""
    tmp_mgr = MagicMock()
    tmp_mgr.make_dir.return_value = "/tmp/nowires_test2"

    result = _project_or_temp_dir(tmp_mgr, context, None, "test_subdir2")
    assert result == "/tmp/nowires_test2"
    tmp_mgr.make_dir.assert_called_once_with("test_subdir2", persistent=True)
    tmp_mgr.warn_persistent.assert_called_once_with(None)


def test_saved_project_uses_project_dir(tmp_path):
    """Saved project returns a directory next to the project file."""
    qgz = tmp_path / "my_map.qgz"
    qgz.write_text("")
    context = MagicMock()
    context.project().fileName.return_value = str(qgz)
    tmp_mgr = MagicMock()

    result = _project_or_temp_dir(tmp_mgr, context, None, "coverage_prx")
    assert result == str(tmp_path / "nowires_coverage_prx")
    assert os.path.isdir(result)
    tmp_mgr.make_dir.assert_not_called()
    tmp_mgr.warn_persistent.assert_not_called()


def test_helper_module_is_importable():
    """The helper module must be importable as a NoWires submodule."""
    import importlib
    mod = importlib.import_module("NoWires.algorithm._project_paths")
    assert hasattr(mod, "_project_or_temp_dir")
