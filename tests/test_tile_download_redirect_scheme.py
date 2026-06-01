# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT




class _RedirectResponse:
    def __init__(self, final_url, body=b"x" * 3601):
        self._final_url = final_url
        self._body = body
        self._pos = 0
        self.headers = {}

    def geturl(self):
        return self._final_url

    def read(self, size=-1):
        remaining = len(self._body) - self._pos
        chunk = min(size if size > 0 else remaining, remaining)
        if chunk <= 0:
            return b""
        data = self._body[self._pos:self._pos + chunk]
        self._pos += chunk
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _SchemeDowngradeOpener:
    def open(self, url, timeout=None):
        return _RedirectResponse("http://evil.example.com/tile.tif")


class _SameSchemeOpener:
    def open(self, url, timeout=None):
        return _RedirectResponse("https://good.example.com/tile.tif")


class _FakeDataset:
    RasterCount = 1
    RasterXSize = 256
    RasterYSize = 256

    def GetRasterBand(self, _idx):
        return None


class TestRedirectScheme:
    def test_https_to_http_scheme_downgrade_rejected(self, tmp_path):
        from NoWires.tile_download_base import download_tile_with_retry
        local_tif = str(tmp_path / "tile.tif")
        result = download_tile_with_retry(
            "https://good.example.com/tile.tif",
            local_tif,
            "test_tile",
            base_url="https://good.example.com/",
            opener=_SchemeDowngradeOpener(),
            max_retries=1,
        )
        assert result is None

    def test_same_scheme_allowed(self, tmp_path, monkeypatch):
        from NoWires import tile_download_base
        monkeypatch.setattr(tile_download_base.gdal, "Open", lambda _path: _FakeDataset())
        local_tif = str(tmp_path / "tile.tif")
        result = tile_download_base.download_tile_with_retry(
            "https://good.example.com/tile.tif",
            local_tif,
            "test_tile",
            base_url="https://good.example.com/",
            opener=_SameSchemeOpener(),
            max_retries=1,
        )
        assert result is not None
        assert result == local_tif
