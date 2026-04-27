# -*- coding: utf-8 -*-
"""Unit tests for worldcover_downloader — ESA WorldCover tile naming and computation."""

import pytest

from worldcover_downloader import (
    worldcover_tile_id,
    required_worldcover_tiles,
    WORLDCOVER_BASE_URL,
)


def test_worldcover_tile_id_north_east():
    assert worldcover_tile_id(0, 0) == "N00E000"
    assert worldcover_tile_id(1, 7) == "N00E006"
    assert worldcover_tile_id(45, 12) == "N45E012"
    assert worldcover_tile_id(14, 121) == "N12E120"


def test_worldcover_tile_id_south_west():
    assert worldcover_tile_id(-1, -1) == "S03W003"
    assert worldcover_tile_id(-14, -121) == "S15W123"


def test_worldcover_tile_id_snaps_to_3deg_grid():
    assert worldcover_tile_id(2, 2) == "N00E000"
    assert worldcover_tile_id(5, 11) == "N03E009"


def test_required_worldcover_tiles_covers_bounding_box():
    tiles = required_worldcover_tiles(13.5, 14.5, 120.5, 122.0)
    assert "N12E120" in tiles
    assert "N12E123" not in tiles


def test_required_worldcover_tiles_single_tile():
    tiles = required_worldcover_tiles(0.5, 1.5, 10.5, 11.5)
    assert tiles == ["N00E009"]


def test_required_worldcover_tiles_crosses_multiple_tiles():
    tiles = required_worldcover_tiles(0.0, 10.0, 0.0, 10.0)
    assert "N00E000" in tiles
    assert "N00E003" in tiles
    assert "N03E000" in tiles
    assert "N03E003" in tiles
    assert len(tiles) == 16


def test_base_url_points_to_esa_worldcover():
    assert "esa-worldcover" in WORLDCOVER_BASE_URL
    assert WORLDCOVER_BASE_URL.endswith("/")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])