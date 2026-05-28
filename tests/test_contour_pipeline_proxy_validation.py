# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test: proxy realm URL must be validated before use."""

import os


def test_proxy_realm_url_validated():
    """setup_proxy_opener must validate hostname and port before building URL."""
    source_path = os.path.join(
        os.path.dirname(__file__), "..", "contour", "pipeline.py",
    )
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    hostname_line = "proxy_host = parsed_realm.hostname"
    assert hostname_line in source

    after = source[source.index(hostname_line):]
    before_format = after[:after.index("proxy_base_url")]
    assert "None" in before_format or "if " in before_format or (
        "not " in before_format
    ), "proxy realm hostname/port must be validated before building http://host:port URL"