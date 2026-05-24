# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
        email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/


Shared helpers for writing simple NoWires report exports.
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from NoWires.sanitizers import csv_safe, sanitize_json


def _iter_rows(payload):
    """Yield CSV rows as (section, key, value) tuples."""
    for section_name, section_value in payload.items():
        if isinstance(section_value, dict):
            for key, value in section_value.items():
                yield section_name, key, value
        else:
            yield "meta", section_name, section_value


def write_report_csv(path, payload):
    """Write a report payload as section/key/value CSV."""
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "key", "value"])
        for row in _iter_rows(payload):
            writer.writerow(tuple(csv_safe(v) for v in row))


def write_report_json(path, payload):
    """Write a report payload as indented JSON."""
    path = Path(path)
    sanitized = sanitize_json(payload)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(sanitized, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def build_html_document(payload, title):
    """Return the HTML document body used by both HTML and PDF writers."""
    sections = []
    for section_name, section_value in payload.items():
        if not isinstance(section_value, dict):
            continue
        rows = "".join(
            "<tr><th>{}</th><td>{}</td></tr>".format(
                html.escape(str(key)), html.escape(str(value))
            )
            for key, value in section_value.items()
        )
        sections.append(
            "<section><h2>{}</h2><table>{}</table></section>".format(
                html.escape(section_name.replace("_", " ").title()), rows
            )
        )
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #1f2933; }}
      h1, h2 {{ margin: 0 0 12px; }}
      section {{ margin: 0 0 20px; }}
      table {{ border-collapse: collapse; width: 100%; max-width: 960px; }}
      th, td {{ border: 1px solid #cbd2d9; padding: 8px 10px; text-align: left; }}
      th {{ background: #f5f7fa; width: 32%; }}
      .summary {{ margin: 0 0 20px; padding: 12px; background: #f5f7fa; }}
    </style>
  </head>
  <body>
    <h1>{title}</h1>
    <div class="summary">{summary}</div>
    {sections}
  </body>
</html>
""".format(
        title=html.escape(title),
        summary=html.escape(str(payload.get("status", {}).get("summary", ""))),
        sections="".join(sections),
    )


def write_report_html(path, payload, title):
    """Write a plain printable HTML report."""
    Path(path).write_text(build_html_document(payload, title), encoding="utf-8")
