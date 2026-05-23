# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import json
from NoWires.batch.writer import write_batch_csv, write_batch_json


def _make_result(status="VIABLE"):
    return {
        "tx_lat": 47.0, "tx_lon": 8.0,
        "rx_lat": 47.1, "rx_lon": 8.1,
        "dist_km": 12.5, "itm_loss_db": 110.0,
        "total_loss_db": 115.0, "margin_db": 5.0,
        "clearance_pct": 60.0, "status": status,
    }


def test_write_batch_csv_one_to_many_mode(tmp_path):
    out = tmp_path / "batch.csv"
    write_batch_csv(str(out), [_make_result(), _make_result("MARGINAL")], mode=0)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3  # header + 2 data rows


def test_write_batch_csv_many_to_one_mode(tmp_path):
    out = tmp_path / "batch.csv"
    write_batch_csv(str(out), [_make_result()], mode=1)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2  # header + 1 data row


def test_write_batch_json_one_to_many(tmp_path):
    out = tmp_path / "batch.json"
    write_batch_json(str(out), [_make_result()], mode=0)
    with open(out) as f:
        data = json.load(f)
    assert "results" in data


def test_write_batch_json_many_to_one(tmp_path):
    out = tmp_path / "batch.json"
    write_batch_json(str(out), [_make_result("VIABLE")], mode=1)
    with open(out) as f:
        data = json.load(f)
    assert "results" in data


def test_write_batch_csv_empty_results(tmp_path):
    out = tmp_path / "batch.csv"
    write_batch_csv(str(out), [], mode=0)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 1  # header only, no data rows
