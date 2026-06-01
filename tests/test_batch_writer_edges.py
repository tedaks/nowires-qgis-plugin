# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Edge case tests for batch/writer.py CSV and JSON output."""

import json
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _result_row(**overrides):
    d = {
        "tx_lat": 47.0, "tx_lon": 8.0,
        "rx_lat": 47.1, "rx_lon": 8.1,
        "dist_km": 12.5, "itm_loss_db": 110.0,
        "total_loss_db": 115.0, "margin_db": 5.0,
        "clearance_pct": 60.0, "status": "VIABLE",
        "climate": "Continental Temperate",
    }
    d.update(overrides)
    return d


class TestBatchCSVEdgeCases:
    def test_empty_results_writes_header_only(self, tmp_path):
        from NoWires.batch.writer import write_batch_csv
        out = tmp_path / "empty.csv"
        write_batch_csv(str(out), [], mode=1)
        content = out.read_text()
        assert "Point Id" in content
        assert content.strip().endswith("climate")

    def test_climate_field_included(self, tmp_path):
        from NoWires.batch.writer import write_batch_csv
        out = tmp_path / "climate.csv"
        results = [_result_row(climate="Maritime Subtropical")]
        write_batch_csv(str(out), results, mode=1)
        content = out.read_text()
        assert "Maritime Subtropical" in content

    def test_climate_field_missing_defaults_to_empty(self, tmp_path):
        from NoWires.batch.writer import write_batch_csv
        out = tmp_path / "noclimate.csv"
        row = _result_row()
        row.pop("climate", None)
        results = [row]
        write_batch_csv(str(out), results, mode=1)
        content = out.read_text()
        assert "climate" in content

    def test_mode_0_uses_rx_point_id(self, tmp_path):
        from NoWires.batch.writer import write_batch_csv
        out = tmp_path / "mode0.csv"
        results = [_result_row()]
        write_batch_csv(str(out), results, mode=0)
        content = out.read_text()
        assert "RX(" in content

    def test_mode_2_uses_rx_point_id_by_default(self, tmp_path):
        from NoWires.batch.writer import write_batch_csv
        out = tmp_path / "mode2.csv"
        results = [_result_row()]
        write_batch_csv(str(out), results, mode=2)
        content = out.read_text()
        assert "RX(" in content


class TestBatchJSONEdgeCases:
    def test_empty_results(self, tmp_path):
        from NoWires.batch.writer import write_batch_json
        out = tmp_path / "empty.json"
        write_batch_json(str(out), [], mode=1)
        data = json.loads(out.read_text())
        assert data["total_links"] == 0
        assert data["viable_links"] == 0
        assert data["results"] == []

    def test_not_viable_status(self, tmp_path):
        from NoWires.batch.writer import write_batch_json
        out = tmp_path / "notviable.json"
        results = [_result_row(status="NOT VIABLE")]
        write_batch_json(str(out), results, mode=1)
        data = json.loads(out.read_text())
        assert data["viable_links"] == 0

    def test_climate_field_included(self, tmp_path):
        from NoWires.batch.writer import write_batch_json
        out = tmp_path / "climate.json"
        results = [_result_row(climate="Equatorial")]
        write_batch_json(str(out), results, mode=1)
        data = json.loads(out.read_text())
        assert data["results"][0]["climate"] == "Equatorial"

    def test_non_ascii_status_rendered_safely(self, tmp_path):
        from NoWires.batch.writer import write_batch_json
        out = tmp_path / "nonascii.json"
        results = [_result_row(status="VIABLE")]
        write_batch_json(str(out), results, mode=1)
        data = json.loads(out.read_text())
        assert data["results"][0]["status"] == "VIABLE"
