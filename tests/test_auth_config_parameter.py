# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Verify QgsProcessingParameterAuthConfig and QgsAuthMethodConfig APIs in QGIS 4."""

import os
import pytest

try:
    from qgis.core import QgsProcessingParameterAuthConfig
    _HAS_QGIS = bool(os.environ.get("QGIS_PREFIX_PATH"))
except ImportError:
    _HAS_QGIS = False

pytestmark = [
    pytest.mark.skipif(
        not _HAS_QGIS,
        reason="QGIS integration tests require QGIS_PREFIX_PATH to be set",
    ),
    pytest.mark.qgis_integration,
]


class TestAuthConfigParameter:
    def test_auth_config_parameter_creation(self, qgis_app):
        param = QgsProcessingParameterAuthConfig("PROXY_AUTH", "Proxy auth", optional=True)
        assert param is not None
        assert param.name() == "PROXY_AUTH"

    def test_auth_config_parameter_optional_flag(self, qgis_app):
        from qgis.core import QgsProcessingParameterAuthConfig
        param = QgsProcessingParameterAuthConfig("PROXY_AUTH", "Proxy auth", optional=True)
        assert param.flags() & QgsProcessingParameterAuthConfig.Flag.FlagOptional

    def test_qgs_auth_method_config_can_be_created(self, qgis_app):
        try:
            from qgis.core import QgsAuthMethodConfig
            config = QgsAuthMethodConfig()
            assert config is not None
            config.setId("test_config")
            config.setName("Test Config")
            config.setMethod("Basic")
            assert config.id() == "test_config"
        except (ImportError, AttributeError):
            pytest.skip("QgsAuthMethodConfig not available in this QGIS build")