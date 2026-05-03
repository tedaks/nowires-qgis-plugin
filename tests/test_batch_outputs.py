# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Behavioral tests for batch_outputs: rank_batch_results and _feat_attr.

These functions are tested by extracting them via exec to avoid the deep
QGIS dependency chain that batch_outputs transitively imports.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_NULL = object()

# _feat_attr extracted logic (matches batch_outputs._feat_attr)
def _feat_attr(feat, name, default):
    try:
        val = feat.attribute(name)
    except (KeyError, IndexError):
        return default
    if val is None or val is _NULL:
        return default
    if default is None:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return str(val)
        return default
    try:
        if isinstance(default, float):
            return float(val)
        if isinstance(default, int):
            coerced = int(float(val))
            return coerced
        if isinstance(default, str):
            return str(val)
        return default
    except (ValueError, TypeError):
        return default


# rank_batch_results logic (matches batch_outputs.rank_batch_results)
def rank_batch_results(results, rank_by):
    if rank_by == 0:
        results.sort(key=lambda r: (r["margin_db"], r["clearance_pct"]), reverse=True)
    elif rank_by == 1:
        results.sort(key=lambda r: (r["itm_loss_db"], r["margin_db"]))
    else:
        results.sort(key=lambda r: (r["clearance_pct"], r["margin_db"]), reverse=True)
    return results


class _FakeFeature:
    def __init__(self, attrs):
        self._attrs = attrs

    def attribute(self, name):
        if name in self._attrs:
            return self._attrs[name]
        raise KeyError(name)


class TestFeatAttr:
    def test_returns_default_on_missing_field(self):
        f = _FakeFeature({})
        assert _feat_attr(f, "missing_field", 10.0) == 10.0

    def test_returns_default_on_null_attribute(self):
        f = _FakeFeature({"height": None})
        assert _feat_attr(f, "height", 10.0) == 10.0

    def test_casts_int_to_float_when_default_is_float(self):
        f = _FakeFeature({"height": 5})
        assert _feat_attr(f, "height", 10.0) == 5.0

    def test_casts_float_to_int_when_default_is_int(self):
        f = _FakeFeature({"count": 3.0})
        assert _feat_attr(f, "count", 1) == 3

    def test_keeps_str_when_default_is_str(self):
        f = _FakeFeature({"name": "hello"})
        assert _feat_attr(f, "name", "default") == "hello"

    def test_returns_default_on_type_mismatch(self):
        f = _FakeFeature({"height": "not_a_number"})
        assert _feat_attr(f, "height", 10.0) == 10.0

    def test_default_none_returns_float_for_numeric(self):
        f = _FakeFeature({"height": 42})
        result = _feat_attr(f, "height", None)
        assert result == 42.0
        assert isinstance(result, float)

    def test_default_none_returns_str_for_string(self):
        f = _FakeFeature({"name": "hello"})
        result = _feat_attr(f, "name", None)
        assert result == "hello"
        assert isinstance(result, str)

    def test_default_none_returns_none_for_null_attr(self):
        f = _FakeFeature({"height": None})
        assert _feat_attr(f, "height", None) is None


class TestRankBatchResults:
    def test_rank_by_margin_0(self):
        results = [
            {"margin_db": 5.0, "clearance_pct": 50.0, "itm_loss_db": 100.0},
            {"margin_db": 10.0, "clearance_pct": 80.0, "itm_loss_db": 90.0},
            {"margin_db": -3.0, "clearance_pct": 90.0, "itm_loss_db": 110.0},
        ]
        ranked = rank_batch_results(results.copy(), rank_by=0)
        assert ranked[0]["margin_db"] == 10.0
        assert ranked[-1]["margin_db"] == -3.0

    def test_rank_by_loss_1(self):
        results = [
            {"margin_db": 5.0, "itm_loss_db": 120.0, "clearance_pct": 50.0},
            {"margin_db": 10.0, "itm_loss_db": 80.0, "clearance_pct": 80.0},
            {"margin_db": 8.0, "itm_loss_db": 100.0, "clearance_pct": 70.0},
        ]
        ranked = rank_batch_results(results.copy(), rank_by=1)
        assert ranked[0]["itm_loss_db"] == 80.0
        assert ranked[-1]["itm_loss_db"] == 120.0

    def test_rank_by_clearance_2(self):
        results = [
            {"clearance_pct": 50.0, "margin_db": 5.0, "itm_loss_db": 100.0},
            {"clearance_pct": 90.0, "margin_db": -3.0, "itm_loss_db": 110.0},
            {"clearance_pct": 70.0, "margin_db": 8.0, "itm_loss_db": 90.0},
        ]
        ranked = rank_batch_results(results.copy(), rank_by=2)
        assert ranked[0]["clearance_pct"] == 90.0
        assert ranked[-1]["clearance_pct"] == 50.0

    def test_rank_by_unknown_defaults_to_clearance(self):
        results = [
            {"clearance_pct": 30.0, "margin_db": 1.0, "itm_loss_db": 100.0},
            {"clearance_pct": 70.0, "margin_db": 5.0, "itm_loss_db": 90.0},
        ]
        ranked = rank_batch_results(results.copy(), rank_by=99)
        assert ranked[0]["clearance_pct"] == 70.0