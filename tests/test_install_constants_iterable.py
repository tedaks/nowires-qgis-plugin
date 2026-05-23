# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from NoWires.base_algorithm import install_constants


def test_install_constants_with_tuple():
    cls = type("TestCls", (), {})
    install_constants(cls, ("A", "B", "C"))
    assert cls.A == "A"
    assert cls.B == "B"
    assert cls.C == "C"


def test_install_constants_with_list():
    cls = type("TestCls", (), {})
    install_constants(cls, ["X", "Y"])
    assert cls.X == "X"
    assert cls.Y == "Y"
