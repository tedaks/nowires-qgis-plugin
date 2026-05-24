# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.3 — released 2026-05-24

All planned items landed. See [CHANGELOG.md](CHANGELOG.md#163---2026-05-24) for details.

## v1.6.4 — coverage push

Target: 85% combined unit + integration test coverage (current: 63% unit, ~68% combined).

- Increase `fail_under` coverage threshold from 59% to 65% in `pyproject.toml`.
- Move remaining orphaned standalone scripts (`run_coverage.py`, `analyze_coverage.py`, `export_portable.py`, `export_project.py`, `package_gpkg.py`, `audit_cache.py`) to `scripts/` directory and add `scripts/*` to `[tool.coverage.run] omit`.
- Add unit tests for high-value uncovered modules: `elevation.py` bearing-destination paths, `tile_download_base.py` retry/cancel/corruption branches, `nowires.py` plugin lifecycle/init paths, `batch/outputs.py` ITM result handling, `batch/writer.py` CSV edge cases, `radio_coverage/pool.py` close/unlink/fallback, `contour/smoothing.py` and `_smoothing_vrt.py` kernel/VRT helpers.
- Add Docker-based QGIS integration tests for algorithm orchestration: `algorithm/batch.py` full processAlgorithm, `algorithm/coverage_comparison.py` panel execution, `algorithm/contour.py` pipeline integration, `algorithm/coverage.py` clutter context/outputs, `comparison/outputs.py` full output writing.
- Add unit tests for non-Qt paths in GUI modules: `three_d.py` terrain configuration, `report/markers.py` marker parameterization, `radio_coverage/legend.py` legend data builders, `p2p/chart.py` chart data assembly.
