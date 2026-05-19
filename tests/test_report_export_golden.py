# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Golden-file regression tests for report_export.

Catches accidental drift in CSV/JSON/HTML output format, which is consumed
by users opening the saved report files. A field rename or escape-rule
change should fail loudly here rather than ship silently.
"""

import json
import math

from report.export import write_report_csv, write_report_html, write_report_json


def _fixture_payload():
    """Minimal payload that exercises each format quirk in one place."""
    return {
        "status": {"summary": "Link viable, margin +6.2 dB"},
        "geometry": {
            "tx_lat": 47.6062,
            "tx_lon": -122.3321,
            "distance_km": 12.34,
        },
        "link": {
            # NaN and inf must round-trip as null in JSON (allow_nan=False).
            "fade_margin_db": 6.2,
            "loss_nan": float("nan"),
            "loss_inf": float("inf"),
        },
        "safety": {
            # CSV must prefix formula-injection characters with a quote.
            "csv_formula": "=SUM(A1)",
            "csv_email_at": "@evil",
            "csv_negative": "-not-a-number",
            "html_xss": "<script>alert(1)</script>",
        },
        "scalar_meta": "top-level non-dict goes to the 'meta' section",
    }


def test_csv_golden_format(tmp_path):
    out = tmp_path / "r.csv"
    write_report_csv(out, _fixture_payload())
    # Read with universal newlines so this is platform-stable; csv.writer
    # emits \r\n but Python text mode normalizes to \n on read.
    text = out.read_text(encoding="utf-8")
    expected = (
        "section,key,value\n"
        "status,summary,\"Link viable, margin +6.2 dB\"\n"
        "geometry,tx_lat,47.6062\n"
        "geometry,tx_lon,-122.3321\n"
        "geometry,distance_km,12.34\n"
        "link,fade_margin_db,6.2\n"
        "link,loss_nan,nan\n"
        "link,loss_inf,inf\n"
        "safety,csv_formula,'=SUM(A1)\n"
        "safety,csv_email_at,'@evil\n"
        "safety,csv_negative,'-not-a-number\n"
        "safety,html_xss,<script>alert(1)</script>\n"
        "meta,scalar_meta,top-level non-dict goes to the 'meta' section\n"
    )
    assert text == expected, "CSV drift:\n--- got ---\n{}\n--- want ---\n{}".format(
        text, expected
    )


def test_json_golden_format(tmp_path):
    out = tmp_path / "r.json"
    write_report_json(out, _fixture_payload())
    data = json.loads(out.read_text(encoding="utf-8"))
    # NaN/inf round-trip as null (sanitize_json).
    assert data["link"]["loss_nan"] is None
    assert data["link"]["loss_inf"] is None
    # Finite floats preserved.
    assert math.isclose(data["link"]["fade_margin_db"], 6.2)
    # Keys are sorted (json.dump sort_keys=True).
    assert list(data.keys()) == sorted(data.keys()), data.keys()
    # Top-level scalar key is preserved verbatim.
    assert data["scalar_meta"].startswith("top-level non-dict")


def test_json_golden_text_exact(tmp_path):
    out = tmp_path / "r.json"
    write_report_json(out, _fixture_payload())
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n"), "JSON must end with newline"
    # Indented with 2 spaces (json.dump indent=2)
    assert "\n  " in text
    # NaN/inf sanitized
    assert "NaN" not in text
    assert "Infinity" not in text


def test_html_golden_format(tmp_path):
    out = tmp_path / "r.html"
    write_report_html(out, _fixture_payload(), title="Smoke Report")
    text = out.read_text(encoding="utf-8")
    # XSS payload must be escaped.
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in text
    # Title is rendered escaped.
    assert "<title>Smoke Report</title>" in text
    assert "<h1>Smoke Report</h1>" in text
    # Status.summary surfaces in the summary div.
    assert "Link viable, margin +6.2 dB" in text
    # Section heading title-cased and underscores stripped.
    assert "<h2>Geometry</h2>" in text
    assert "<h2>Safety</h2>" in text
    # Non-dict top-level keys do NOT render as sections.
    assert "Scalar Meta" not in text


def test_html_golden_doctype_and_charset(tmp_path):
    out = tmp_path / "r.html"
    write_report_html(out, _fixture_payload(), title="x")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in text
