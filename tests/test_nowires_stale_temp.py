# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import tempfile
from unittest import mock
from NoWires.nowires import _stale_temp_dir_count


def test_counts_nowires_temp_dirs(tmp_path):
    for i in range(3):
        os.makedirs(tmp_path / f"nowires_{i}", exist_ok=True)
    with mock.patch.object(tempfile, "gettempdir", return_value=str(tmp_path)):
        result = _stale_temp_dir_count()
    assert result == 3


def test_no_dirs_returns_zero(tmp_path):
    with mock.patch.object(tempfile, "gettempdir", return_value=str(tmp_path)):
        result = _stale_temp_dir_count()
    assert result == 0


def test_oserror_on_listdir_returns_zero():
    with mock.patch.object(tempfile, "gettempdir", return_value="/nonexistent"):
        result = _stale_temp_dir_count()
    assert result == 0


def test_returns_int_type():
    result = _stale_temp_dir_count()
    assert isinstance(result, int)
