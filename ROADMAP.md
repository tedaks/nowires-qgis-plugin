# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.3 (planned)

- Add import-linter contracts for layering violations: `radio` must not depend on `radio_coverage`, `raster_io` must not depend on `radio_coverage`, `tile_download_base` must not depend on `report`.
- Extract `_csv_safe` and `_sanitize_json` from `report/export.py` to a shared utility module, removing cross-subpackage private-symbol imports in `batch/writer.py`.
- Add `GDAL_DRIVER_NAME = "GTiff"` and `AOI_PADDING_FRACTION = 0.1` to `constants.py`, replacing 8 and 4 hardcoded occurrences respectively.
- Extract duplicated AOI padding formula (`max(DEGREE_PADDING, ... * METERS_PER_DEGREE_LAT * 0.1)`) into a shared utility function.
- Pre-emptively split `tile_download_base.py` (currently at 300-line project limit).
- Clamp `math.asin` argument in `elevation.py:bearing_destination` to `[-1.0, 1.0]` for large distances.
- Replace `itm_p2p_loss()` hardcoded parameter defaults (`301.0`, `300.0`, `15.0`, `0.005`) with imports from `defaults.py`.
- Increase `mypy` strictness: replace `type: ignore[arg-type]` suppressions in `comparison/reporting.py` with explicit `assert` guards.
- Write unit tests for `comparison/add_params.py` (298 lines, currently untested).
- Remove stale test comment at `test_algorithms_integration.py:90-100` documenting the pre-v1.6.2 PANEL_A/PANEL_B bug that is now fixed.
- Add `__all__` to top-level `__init__.py` for explicit public API surface.
- Make `clutter/__init__.py` stop re-exporting underscore-prefixed private symbols (`_category_height_m`, `_resolve_category`).
- Move orphaned standalone scripts (`export_portable.py`, `export_project.py`, `run_coverage.py`, `audit_cache.py`, `analyze_coverage.py`, `package_gpkg.py`) to a `scripts/` directory.
- Add `reviewers` and `labels` to `.github/dependabot.yml`.
- Move `from urllib.parse import urlsplit` from inside `download_tile_with_retry` loop to module level in `tile_download_base.py` — lazy import executes on every tile download attempt.
- Replace hardcoded `earth_r = 6371000.0` in `package_gpkg.py:96` with `EARTH_RADIUS_M` from `constants.py` — same value defined locally instead of importing the shared constant.
- Remove redundant `shared_clutter_grid = None` at `algorithm/coverage_comparison.py:124` — dead store immediately following the same assignment at line 119.
- Remove unnecessary `Qt_rm = QTimer` alias at `p2p/chart.py:149` — `QTimer.singleShot` is a static method; the alias adds no value and the same function calls `QTimer.singleShot` directly at line 168.
- Update bumpversion configuration to add release dates to CHANGELOG headers per Keep a Changelog format.

## v1.6.4 — coverage push

Target: 85% combined unit + integration test coverage (current: 63% unit, ~68% combined).

- Increase `fail_under` coverage threshold from 59% to 65% in `pyproject.toml`.
- Move orphaned standalone scripts (`run_coverage.py`, `analyze_coverage.py`, `export_portable.py`, `export_project.py`, `package_gpkg.py`, `audit_cache.py`) to `scripts/` directory and add `scripts/*` to `[tool.coverage.run] omit` to exclude zero-coverage utility scripts from the denominator. *(Note: overlaps with v1.6.3 script-move item — keep in whichever release ships first.)*
- Add unit tests for high-value uncovered modules: `elevation.py` bearing-destination paths, `tile_download_base.py` retry/cancel/corruption branches, `nowires.py` plugin lifecycle/init paths, `batch/outputs.py` ITM result handling, `batch/writer.py` CSV edge cases, `radio_coverage/pool.py` close/unlink/fallback, `contour/smoothing.py` and `_smoothing_vrt.py` kernel/VRT helpers.
- Add Docker-based QGIS integration tests for algorithm orchestration: `algorithm/batch.py` full processAlgorithm, `algorithm/coverage_comparison.py` panel execution, `algorithm/contour.py` pipeline integration, `algorithm/coverage.py` clutter context/outputs, `comparison/outputs.py` full output writing.
- Add unit tests for non-Qt paths in GUI modules: `three_d.py` terrain configuration, `report/markers.py` marker parameterization, `radio_coverage/legend.py` legend data builders, `p2p/chart.py` chart data assembly.
