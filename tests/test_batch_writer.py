# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for batch_writer: write_batch_csv and write_batch_json."""

import csv
import json

from NoWires.batch.writer import write_batch_csv, write_batch_json
from batch.params import BATCH_MODE_OPTIONS

SAMPLE_RESULTS = [
    {
        "tx_lat": 14.0,
        "tx_lon": 121.0,
        "rx_lat": 14.01,
        "rx_lon": 121.01,
        "dist_km": 1.5678,
        "itm_loss_db": 120.567,
        "total_loss_db": 125.836,
        "margin_db": 10.234,
        "clearance_pct": 45.67,
        "status": "VIABLE",
        "climate": "Continental Temperate",
    },
    {
        "tx_lat": 14.5,
        "tx_lon": 121.5,
        "rx_lat": 14.51,
        "rx_lon": 121.51,
        "dist_km": 2.3456,
        "itm_loss_db": 130.123,
        "total_loss_db": 135.678,
        "margin_db": -2.345,
        "clearance_pct": 20.89,
        "status": "NOT VIABLE",
        "climate": "Continental Temperate",
    },
]

EXPECTED_HEADERS = [
    "Point Id", "rank", "tx_lat", "tx_lon", "rx_lat", "rx_lon",
    "dist_km", "itm_loss_db", "total_loss_db",
    "margin_db", "clearance_pct", "status", "climate",
]


class TestWriteBatchCsv:
    def test_mode1_tx_formats_point_id(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[1][0] == "TX(1, 14.00000, 121.00000)"
        assert rows[2][0] == "TX(2, 14.50000, 121.50000)"

    def test_mode2_rx_formats_point_id(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), SAMPLE_RESULTS, mode=2)
        with open(str(path), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[1][0] == "RX(1, 14.01000, 121.01000)"
        assert rows[2][0] == "RX(2, 14.51000, 121.51000)"

    def test_header_row_matches_expected(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[0] == EXPECTED_HEADERS

    def test_numeric_rounding(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), [SAMPLE_RESULTS[0]], mode=1)
        with open(str(path), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        row = rows[1]
        assert row[6] == "1.568"
        assert row[7] == "120.57"
        assert row[8] == "125.84"
        assert row[9] == "10.23"
        assert row[10] == "45.7"

    def test_empty_results_list(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), [], mode=1)
        with open(str(path), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1
        assert rows[0] == EXPECTED_HEADERS

    def test_multiple_results(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 3

    def test_file_written_as_utf8(self, tmp_path):
        path = tmp_path / "out.csv"
        write_batch_csv(str(path), SAMPLE_RESULTS, mode=1)
        raw = path.read_bytes()
        decoded = raw.decode("utf-8")
        assert "Point Id" in decoded


class TestWriteBatchJson:
    def test_report_type(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["report_type"] == "batch_p2p"

    def test_generated_by(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["generated_by"] == "NoWires"

    def test_mode_mapping_tx(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["mode"] == BATCH_MODE_OPTIONS[1]

    def test_mode_mapping_rx(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=0)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["mode"] == BATCH_MODE_OPTIONS[0]

    def test_total_links_count(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_links"] == 2

    def test_viable_links_count(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["viable_links"] == 1

    def test_numeric_rounding_in_results(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), [SAMPLE_RESULTS[0]], mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        r = data["results"][0]
        assert r["distance_km"] == 1.568
        assert r["itm_loss_db"] == 120.57
        assert r["total_loss_db"] == 125.84
        assert r["margin_db"] == 10.23
        assert r["clearance_pct"] == 45.7

    def test_status_preservation(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), SAMPLE_RESULTS, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["results"][0]["status"] == "VIABLE"
        assert data["results"][1]["status"] == "NOT VIABLE"

    def test_empty_results_zero_counts(self, tmp_path):
        path = tmp_path / "out.json"
        write_batch_json(str(path), [], mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_links"] == 0
        assert data["viable_links"] == 0
        assert data["results"] == []

    def test_all_not_viable_zero_viable(self, tmp_path):
        not_viable = [
            {
                "tx_lat": 14.0, "tx_lon": 121.0,
                "rx_lat": 14.01, "rx_lon": 121.01,
                "dist_km": 1.5, "itm_loss_db": 130.0,
                "total_loss_db": 140.0, "margin_db": -5.0,
                "clearance_pct": 10.0, "status": "NOT VIABLE",
                "climate": "Equatorial",
            },
            {
                "tx_lat": 14.5, "tx_lon": 121.5,
                "rx_lat": 14.51, "rx_lon": 121.51,
                "dist_km": 2.0, "itm_loss_db": 140.0,
                "total_loss_db": 150.0, "margin_db": -10.0,
                "clearance_pct": 5.0, "status": "NOT VIABLE",
                "climate": "Equatorial",
            },
        ]
        path = tmp_path / "out.json"
        write_batch_json(str(path), not_viable, mode=0)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_links"] == 2
        assert data["viable_links"] == 0

    def test_all_viable_count_matches(self, tmp_path):
        viable = [
            {
                "tx_lat": 14.0, "tx_lon": 121.0,
                "rx_lat": 14.01, "rx_lon": 121.01,
                "dist_km": 1.5, "itm_loss_db": 100.0,
                "total_loss_db": 110.0, "margin_db": 15.0,
                "clearance_pct": 80.0, "status": "VIABLE",
                "climate": "Maritime Temperate",
            },
            {
                "tx_lat": 14.5, "tx_lon": 121.5,
                "rx_lat": 14.51, "rx_lon": 121.51,
                "dist_km": 2.0, "itm_loss_db": 105.0,
                "total_loss_db": 115.0, "margin_db": 12.0,
                "clearance_pct": 70.0, "status": "VIABLE",
                "climate": "Maritime Temperate",
            },
        ]
        path = tmp_path / "out.json"
        write_batch_json(str(path), viable, mode=1)
        with open(str(path), encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_links"] == 2
        assert data["viable_links"] == 2