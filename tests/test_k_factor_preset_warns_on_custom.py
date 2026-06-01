# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test: resolve_k_factor warns when both preset and custom K_FACTOR supplied.

When a K_FACTOR_PRESET is selected AND a custom K_FACTOR value is supplied,
resolve_k_factor must emit a warning that the custom value is being ignored
in favor of the preset.
"""

import logging

from radio import K_FACTOR_PRESETS, resolve_k_factor


def test_resolve_k_factor_warns_on_custom_override(caplog):
    """resolve_k_factor logs warning when preset + custom both present."""
    custom_value = 1.5
    preset_index = 0

    with caplog.at_level(logging.WARNING):
        result = resolve_k_factor(
            has_preset=True, has_custom=True,
            custom_value=custom_value, preset_index=preset_index,
        )

    assert result == K_FACTOR_PRESETS[preset_index]
    assert any(
        "custom K_FACTOR" in record.message and "ignored" in record.message
        for record in caplog.records
    ), (
        "No warning logged when K_FACTOR custom value is ignored. "
        "Expected a warning about custom K_FACTOR being ignored in favor of preset."
    )


def test_no_warning_when_only_preset_or_custom(caplog):
    """No warning when only preset or only custom is supplied."""
    with caplog.at_level(logging.WARNING):
        resolve_k_factor(has_preset=True, has_custom=False, custom_value=0.0, preset_index=2)
    for record in caplog.records:
        assert "custom K_FACTOR" not in record.message

    with caplog.at_level(logging.WARNING):
        resolve_k_factor(has_preset=False, has_custom=True, custom_value=2.5, preset_index=0)
    for record in caplog.records:
        assert "custom K_FACTOR" not in record.message
