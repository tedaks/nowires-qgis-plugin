# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT

import pytest
from NoWires.tile_download_base import _redact_query


class TestURLRedaction:
    @pytest.mark.parametrize("url,expected", [
        ("https://example.com/tile.tif", "https://example.com/tile.tif"),
        ("https://e.com/t.tif?key=secret", "https://e.com/t.tif"),
        ("https://e.com/t.tif?k=v#frag", "https://e.com/t.tif"),
        ("https://e.com/t.tif#frag", "https://e.com/t.tif"),
    ])
    def test_redact_query(self, url, expected):
        assert _redact_query(url) == expected

    def test_presigned_url_signature_stripped(self):
        url = "https://s3.eu-central-1.amazonaws.com/copernicus-dem-30m/Copernicus_DSM_COG_10_N15_00_E120_00_DEM.tif?X-Amz-Signature=deadbeef&X-Amz-Credential=AKIA"
        redacted = _redact_query(url)
        assert "X-Amz-Signature" not in redacted
        assert "AKIA" not in redacted
        assert redacted == "https://s3.eu-central-1.amazonaws.com/copernicus-dem-30m/Copernicus_DSM_COG_10_N15_00_E120_00_DEM.tif"
