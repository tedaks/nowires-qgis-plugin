# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Unit tests for worldcover_downloader — ESA WorldCover tile naming and computation."""

import pytest
from types import SimpleNamespace

from worldcover_downloader import (
    get_worldcover_dir,
    worldcover_tile_id,
    required_worldcover_tiles,
    WORLDCOVER_BASE_URL,
)

import tile_download_base


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


def test_worldcover_cache_directory_is_per_user(tmp_path, monkeypatch):
    import worldcover_downloader as wd

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )

    assert get_worldcover_dir() == str(tmp_path / "NoWires-alice" / "worldcover")


def test_worldcover_cache_directory_sanitizes_username(tmp_path, monkeypatch):
    import worldcover_downloader as wd

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "ali ce:bad/name"),
        raising=False,
    )

    assert get_worldcover_dir() == str(
        tmp_path / "NoWires-ali_ce_bad_name" / "worldcover"
    )


def test_worldcover_cache_directory_uses_default_username_when_lookup_fails(
    tmp_path, monkeypatch
):
    import worldcover_downloader as wd

    def getuser_raises():
        raise KeyError("no user")

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=getuser_raises),
        raising=False,
    )

    assert get_worldcover_dir() == str(tmp_path / "NoWires-nowires" / "worldcover")


def test_worldcover_cache_directory_replaces_existing_child_file(tmp_path, monkeypatch):
    import worldcover_downloader as wd

    target = tmp_path / "NoWires-alice" / "worldcover"
    target.parent.mkdir()
    target.write_text("not a directory", encoding="utf-8")

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )

    assert get_worldcover_dir() == str(target)
    assert target.is_dir()


def test_worldcover_cache_directory_validates_existing_dirs_with_nofollow_flags(
    tmp_path, monkeypatch
):
    import worldcover_downloader as wd

    parent = tmp_path / "NoWires-alice"
    target = parent / "worldcover"
    target.mkdir(parents=True)
    calls = []

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.setattr(wd.os, "O_DIRECTORY", 0x10000, raising=False)
    monkeypatch.setattr(wd.os, "O_NOFOLLOW", 0x20000, raising=False)
    monkeypatch.setattr(wd.os, "open", lambda path, flags: calls.append((path, flags)) or 42)
    monkeypatch.setattr(wd.os, "close", lambda fd: calls.append(("close", fd)))

    assert get_worldcover_dir() == str(target)
    expected_flags = wd.os.O_RDONLY | wd.os.O_DIRECTORY | wd.os.O_NOFOLLOW
    assert calls == [
        (str(parent), expected_flags),
        ("close", 42),
        (str(target), expected_flags),
        ("close", 42),
    ]


def test_worldcover_cache_directory_handles_platforms_without_nofollow_flags(tmp_path, monkeypatch):
    import worldcover_downloader as wd

    target = tmp_path / "NoWires-alice" / "worldcover"
    target.mkdir(parents=True)

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.delattr(wd.os, "O_DIRECTORY", raising=False)
    monkeypatch.delattr(wd.os, "O_NOFOLLOW", raising=False)

    assert get_worldcover_dir() == str(target)


def test_worldcover_cache_directory_uses_fallback_parent_when_parent_rename_fails(
    tmp_path, monkeypatch
):
    import worldcover_downloader as wd

    original_parent = tmp_path / "NoWires-alice"
    original_rename = wd.os.rename

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )

    def rename_fails_for_original_parent(src, dst):
        if dst == str(original_parent):
            raise OSError("simulated cross-platform rename failure")
        original_rename(src, dst)

    monkeypatch.setattr(wd.os, "rename", rename_fails_for_original_parent)

    result = get_worldcover_dir()

    assert result != str(original_parent / "worldcover")
    assert result.endswith("worldcover")
    assert wd.os.path.isdir(result)


def test_worldcover_cache_directory_uses_fallback_child_when_child_rename_fails(
    tmp_path, monkeypatch
):
    import worldcover_downloader as wd

    parent = tmp_path / "NoWires-alice"
    target = parent / "worldcover"
    original_rename = wd.os.rename

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )

    def rename_fails_for_worldcover(src, dst):
        if dst == str(target):
            raise OSError("simulated child rename failure")
        original_rename(src, dst)

    monkeypatch.setattr(wd.os, "rename", rename_fails_for_worldcover)

    result = get_worldcover_dir()

    assert result != str(target)
    assert result.startswith(str(parent))
    assert wd.os.path.isdir(result)


def test_worldcover_cache_directory_does_not_crash_when_existing_dir_open_fails(
    tmp_path, monkeypatch
):
    import worldcover_downloader as wd

    target = tmp_path / "NoWires-alice" / "worldcover"
    target.mkdir(parents=True)

    monkeypatch.setattr(wd.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        wd,
        "getpass",
        SimpleNamespace(getuser=lambda: "alice"),
        raising=False,
    )
    monkeypatch.setattr(wd.os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        OSError("simulated directory open failure")
    ))

    assert get_worldcover_dir() == str(target)


def test_download_worldcover_tiles_replaces_corrupt_cache(tmp_path, monkeypatch):
    import worldcover_downloader as wd

    tile_id = "N00E000"
    local_tif = tmp_path / wd.worldcover_tile_filename(tile_id)
    local_tif.write_bytes(b"corrupt")

    open_calls = []

    class FakeResponse:
        headers = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def geturl(self):
            return wd.worldcover_tile_url(tile_id)

        def read(self, _size):
            if getattr(self, "_read", False):
                return b""
            self._read = True
            return b"good"

    class FakeOpener:
        def open(self, url, timeout):
            open_calls.append((url, timeout))
            return FakeResponse()

    open_results = iter([None, object()])
    monkeypatch.setattr(tile_download_base.gdal, "Open", lambda _path: next(open_results))
    monkeypatch.setattr(wd.urllib.request, "build_opener", lambda *_args, **_kwargs: FakeOpener())

    paths = wd.download_worldcover_tiles([tile_id], temp_dir=str(tmp_path))

    assert paths == [str(local_tif)]
    assert open_calls == [(wd.worldcover_tile_url(tile_id), 120)]
    assert local_tif.read_bytes() == b"good"


def test_download_worldcover_tiles_finalizes_download_with_os_replace(tmp_path, monkeypatch):
    import worldcover_downloader as wd

    tile_id = "N00E000"
    local_tif = tmp_path / wd.worldcover_tile_filename(tile_id)
    replace_calls = []
    original_replace = wd.os.replace

    class FakeResponse:
        headers = {"Content-Length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def geturl(self):
            return wd.worldcover_tile_url(tile_id)

        def read(self, _size):
            if getattr(self, "_read", False):
                return b""
            self._read = True
            return b"good"

    class FakeOpener:
        def open(self, url, timeout):
            return FakeResponse()

    def fake_replace(src, dst):
        replace_calls.append((src, dst))
        original_replace(src, dst)

    monkeypatch.setattr(tile_download_base.gdal, "Open", lambda _path: object())
    monkeypatch.setattr(wd.urllib.request, "build_opener", lambda *_args, **_kwargs: FakeOpener())
    monkeypatch.setattr(wd.os, "replace", fake_replace)

    paths = wd.download_worldcover_tiles([tile_id], temp_dir=str(tmp_path))

    assert paths == [str(local_tif)]
    assert replace_calls == [(str(local_tif) + ".tmp", str(local_tif))]
    assert local_tif.read_bytes() == b"good"


def test_download_worldcover_tiles_removes_leftover_tmp_after_failed_download(tmp_path, monkeypatch):
    import urllib.error
    import worldcover_downloader as wd

    tile_id = "N00E000"
    local_tif = tmp_path / wd.worldcover_tile_filename(tile_id)
    tmp_path_leftover = tmp_path / (wd.worldcover_tile_filename(tile_id) + ".tmp")
    tmp_path_leftover.write_bytes(b"partial")

    class FakeOpener:
        def open(self, url, timeout):
            raise urllib.error.HTTPError(url, 404, "not found", hdrs=None, fp=None)

    monkeypatch.setattr(wd.urllib.request, "build_opener", lambda *_args, **_kwargs: FakeOpener())

    assert wd.download_worldcover_tiles([tile_id], temp_dir=str(tmp_path)) == []
    assert not local_tif.exists()
    assert not tmp_path_leftover.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
