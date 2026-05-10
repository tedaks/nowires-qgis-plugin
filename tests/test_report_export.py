# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Tests for report export helpers."""

from pathlib import Path

from report_export import write_report_csv, write_report_html, write_report_json


def test_write_report_csv_outputs_section_key_value_rows(tmp_path: Path):
    payload = {
        "report_type": "p2p",
        "generated_by": "NoWires",
        "inputs": {"frequency_mhz": 900.0},
        "results": {"margin_db": 12.5},
        "status": {"viable": True},
    }

    output_path = tmp_path / "report.csv"
    write_report_csv(output_path, payload)

    text = output_path.read_text(encoding="utf-8")
    assert "section,key,value" in text
    assert "inputs,frequency_mhz,900.0" in text
    assert "results,margin_db,12.5" in text


def test_write_report_json_preserves_nested_structure(tmp_path: Path):
    payload = {"report_type": "coverage", "results": {"usable_cell_count": 42}}
    output_path = tmp_path / "report.json"

    write_report_json(output_path, payload)

    text = output_path.read_text(encoding="utf-8")
    assert '"report_type": "coverage"' in text
    assert '"usable_cell_count": 42' in text


def test_write_report_html_renders_title_and_tables(tmp_path: Path):
    payload = {
        "report_type": "p2p",
        "generated_by": "NoWires",
        "inputs": {"frequency_mhz": 5800.0},
        "results": {"margin_db": -4.2},
        "status": {"summary": "NOT VIABLE"},
    }

    output_path = tmp_path / "report.html"
    write_report_html(output_path, payload, title="P2P Report")

    text = output_path.read_text(encoding="utf-8")
    assert "<html" in text.lower()
    assert "P2P Report" in text
    assert "NOT VIABLE" in text
    assert "frequency_mhz" in text
