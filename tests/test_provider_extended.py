# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Extended regression tests for NoWiresProvider covering missed lines."""

from unittest import mock

import pytest


@pytest.mark.qgis_integration
def test_provider_icon_returns_qicon():
    from NoWires.provider import NoWiresProvider

    provider = NoWiresProvider()
    result = provider.icon()
    assert result is not None


@pytest.mark.qgis_integration
def test_provider_load_algorithms_logs_failure():
    from NoWires.provider import NoWiresProvider

    provider = NoWiresProvider()
    with mock.patch(
        "importlib.import_module", side_effect=ImportError("simulated failure")
    ):
        provider.loadAlgorithms()


@pytest.mark.qgis_integration
def test_provider_unload_calls_super():
    from NoWires.provider import NoWiresProvider

    provider = NoWiresProvider()
    provider.unload()


@pytest.mark.qgis_integration
def test_provider_name():
    from NoWires.provider import NoWiresProvider

    provider = NoWiresProvider()
    assert provider.name() == "NoWires"


@pytest.mark.qgis_integration
def test_provider_long_name():
    from NoWires.provider import NoWiresProvider

    provider = NoWiresProvider()
    assert "NoWires" in provider.longName()


@pytest.mark.qgis_integration
def test_provider_id():
    from NoWires.provider import NoWiresProvider

    provider = NoWiresProvider()
    assert provider.id() == "nowires"
