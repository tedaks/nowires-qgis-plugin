# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
from NoWires.dem_downloader import tile_name_for


def test_tile_name_for_float_lat():
    assert tile_name_for(14.7, 121.3) == tile_name_for(14, 121)


def test_tile_name_for_float_lon():
    assert tile_name_for(14, 121.7) == tile_name_for(14, 121)


def test_tile_name_for_negative_float():
    assert tile_name_for(-33.4, -70.6) == tile_name_for(-34, -71)


def test_tile_name_for_int_unchanged():
    assert tile_name_for(14, 121) == "Copernicus_DSM_COG_10_N14_00_E121_00_DEM"