# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
# Licensed under the MIT License. See LICENSE.
"""Regression test for batch_writer.write_batch_csv CSV-injection guard (v1.5.7).

The v1.4.0 fix that added _csv_safe() to report_export.write_report_csv was
scoped to the radio_coverage/P2P CSV path only; batch_writer wrote user-influenced
status/point_id values verbatim. Any cell starting with =, +, @, tab, or CR
would be interpreted as a formula by Excel/LibreOffice on CSV open.
"""

import csv

import pytest


def _result_row(status="VIABLE"):
    return {
        "tx_lat": 47.0, "tx_lon": 8.0,
        "rx_lat": 47.1, "rx_lon": 8.1,
        "dist_km": 12.5, "itm_loss_db": 110.0,
        "total_loss_db": 115.0, "margin_db": 5.0,
        "clearance_pct": 60.0, "status": status,
    }


@pytest.mark.parametrize("payload,expected_prefix", [
    ("=cmd|/bin/bash", "'=cmd|/bin/bash"),
    ("+1+1", "'+1+1"),
    ("@SUM(A1:A10)", "'@SUM(A1:A10)"),
    ("\t=2+2", "'\t=2+2"),
    (" =SUM(A1)", "' =SUM(A1)"),
    (" +A1", "' +A1"),
    ("  @SUM", "'  @SUM"),
])
def test_status_starting_with_formula_char_is_sanitized(tmp_path, payload, expected_prefix):
    from NoWires.batch.writer import write_batch_csv

    out = tmp_path / "batch.csv"
    write_batch_csv(str(out), [_result_row(status=payload)], mode=1)

    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert len(rows) == 2
    status_idx = rows[0].index("status")
    cell = rows[1][status_idx]
    assert cell.startswith("'"), (
        "status cell {!r} not escaped for formula char".format(cell)
    )
    assert cell == expected_prefix, (
        "expected {!r}, got {!r}".format(expected_prefix, cell)
    )


def test_status_safe_value_is_untouched(tmp_path):
    """Sanity: ordinary status strings must not be modified."""
    from NoWires.batch.writer import write_batch_csv

    out = tmp_path / "batch.csv"
    write_batch_csv(str(out), [_result_row(status="VIABLE")], mode=1)

    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    status_idx = rows[0].index("status")
    assert rows[1][status_idx] == "VIABLE"


def test_negative_number_status_is_preserved(tmp_path):
    """Negative numbers in a status-like cell should not be escaped as a formula."""
    from NoWires.batch.writer import write_batch_csv

    out = tmp_path / "batch.csv"
    # status of "-12.3" must round-trip as the numeric string; only non-numeric
    # leading-minus values are treated as formula candidates by _csv_safe.
    write_batch_csv(str(out), [_result_row(status="-12.3")], mode=1)

    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    status_idx = rows[0].index("status")
    assert rows[1][status_idx] == "-12.3"
