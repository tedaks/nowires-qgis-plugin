# Changelog

SPDX-License-Identifier: GPL-3.0-or-later

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.3] - 2026-05-16

### Added

- Added `write_report_pdf()` PDF report writer (`report_pdf.py`) using Qt6 `QTextDocument` + `QPrinter`. Wired to Coverage Analysis as a new `OUTPUT_REPORT_PDF` output. Falls back to a warning and returns `False` when Qt print-support isn't available rather than raising.
- Added `AntennaPatternPreviewDialog` (`antenna_pattern_preview.py`) and a "Preview Antenna Pattern" plugin menu action. Loads an antenna pattern CSV and renders a polar plot via `QPainter` — no matplotlib dependency.
- Added `extract_link_budget_params()` and `LinkBudgetBundle` in `shared_params`. Companion to `extract_clutter_params` introduced earlier; deduplicates the 5-double link-budget extraction across `algorithm_p2p`, `algorithm_batch`, and `coverage_params`.
- Added `build_initial_clutter_context()` factory in `clutter_context.py`. Single source of truth for the placeholder `ClutterLossContext(distance=0, rx_ground=0)`; previously constructed inline in both `algorithm_coverage._build_clutter_context` and `coverage_engine._build_clutter_context`.
- Added `NOWIRES_WINDOWS_MP` environment variable to opt Windows into multiprocessing (off by default). `_ensure_path()` already handles the sys.path hardening needed for spawn-mode workers.
- Added `build_html_document()` in `report_export.py` to share the HTML body between HTML and PDF writers.
- Added golden-file regression tests for CSV/JSON/HTML report output (`tests/test_report_export_golden.py`). Catches accidental drift in field names, escape rules, or document structure.
- Added `tests/test_report_pdf.py` — unit test for the Qt-unavailable fallback path plus a qgis_integration test that asserts a real PDF is written.

### Changed

- Refactored `nowires.py` plugin GUI registration to a single `action_specs` table; removed nine duplicated `QAction(...)` blocks. Net –50 lines and easier to add new menu actions.
- Switched `contour_smoothing.py` from monkey-patching `xml.etree.ElementTree.parse = _safe_parse` (which globally mutated the stdlib parser for every importer in the process) to an explicit `_parse_xml()` wrapper.
- Vectorized the elevation-sampling fallback in `coverage_engine._build_rx_ground_grid` via row-by-row `sample_line` calls when `sample_grid` isn't available; 192× fewer Python-level calls at the default grid size for mocked elevation grids.
- Increased sequential coverage progress reporting from 100 buckets to 200 (`_coverage_executor._run_sequential`).
- HTTP retryable and non-retryable failures in `tile_download_base.download_tile_with_retry` now surface status code and retry timing through `feedback.pushInfo` / `pushWarning`; previously these only went to the Python log.
- `_init_cov_pool` no longer raises `RuntimeError("Shared-memory pool already bound")` when a worker is reused across runs — resets stale state and rebinds instead. Friendlier when threading is enabled.
- Added one-line reason comments to every previously-unexplained `# type: ignore` in production source (9 sites).

### Added (previously in 1.5.3)

- Added `ALLOW_THREADING` opt-in on `NoWiresAlgorithm`. Coverage Analysis, Batch P2P, and Coverage Comparison opt their `processAlgorithm()` into the Processing framework's worker-thread runner so the QGIS UI stays responsive during long computations; quick algorithms (P2P, Contour) keep the existing `NoThreading` behaviour.
- Added `DEFAULT_PER_TILE_WALL_CLOCK_BUDGET` (180s) default for `download_tile_with_retry`. Caps the total time spent retrying a single DEM or WorldCover tile so a slow trickle (where `socket_timeout` never fires) cannot stall a coverage run for `socket_timeout × max_retries` seconds.
- Added `get_cache_size()` and `format_cache_size()` to `cache_manager`. The "Clear DEM Cache" menu now reports current cache size and asks for confirmation before deleting.
- Added `ClutterParamBundle` plus `extract_clutter_params()` in `shared_params`. Single helper replaces three ~20-line duplicated extraction blocks in `algorithm_p2p`, `algorithm_batch`, and `coverage_params`.
- Added `test_algorithm_threading_optin.py` source-level contract tests verifying which algorithms opt into threading.
- Added `TestGetCacheSize` tests for the new cache-size helpers.

### Changed

- Increased coverage multiprocessing progress update frequency from every 50 chunks to every 5 chunks (`_coverage_executor.py`) for finer UI feedback.
- Refactored `clear_dem_cache()` to share the `_iter_cache_entries()` + `_entry_size()` helpers used by `get_cache_size()`, removing duplicated glob/walk loops.

## [1.5.2] - 2026-05-15

### Added

- Added `clear_pattern_cache()` API for reloading antenna pattern CSV files without QGIS restart
- Added GDAL `UseExceptions()` at plugin startup for consistent error handling across all GDAL operations
- Added batch algorithm multipart geometry handling with debug logging
- Added contour CRS fallback to EPSG:4326 when context project is unavailable
- Added NaN-aware elevation interpolation in batch P2P computation using `nan_utils`
- Added 8 new test suites: algorithm execution integration, base algorithm integration, raster I/O integration, hypothesis property-based tests for antenna, coverage compute, Fresnel, and radio
- Added CI pipeline: `pytest` on Python 3.12, `pip-audit` dependency scanning, `ruff` lint in integration job, `timeout-minutes` on benchmarks, version/changelog enforcement workflow
- Added concurrency groups with `cancel-in-progress` to all GitHub Actions workflows
- Added two-step pytest isolation in CI: sensitive tests run separately to avoid module state pollution

### Fixed

- Fix `METERS_PER_FOOT` constant incorrectly applied as multiplier for feet-to-meter conversion in contour generation
- Fix missing trailing newlines and import ordering in multiple modules
- Fix mypy compliance: added type annotations to `_geo_utils`, `batch_outputs`, `base_algorithm`, `clutter_advanced`, and 15+ other modules
- Fix dead code removal: unused module-level globals in `coverage_pool`, unused parameters in `coverage_engine`
- Fix CI pipeline: tracked missing `mypy.ini` to prevent type-check failure on checkout
- Fix CI integration job: `continue-on-error: true` removed so QGIS failures now block PRs
- Fix CI integration matrix: removed `release-3_34` (project targets QGIS 4 / Qt 6 only)
- Fix CI integration job: removed redundant explicit test steps already covered by `-m qgis_integration`
- Fix coverage configuration: override `fail_under` to 0 in integration job to avoid false failures from partial integration-only coverage

### Changed

- Integration tests now collect coverage data alongside unit tests for combined analysis
- Updated CONTRIBUTING.md with CI pipeline documentation and local check instructions

## [1.5.1] - 2026-05-12

### Added

- Added "Clear DEM Cache" menu action to remove stale downloaded DEM and WorldCover tiles from the temp directory
- Added `cache_manager.py` module with size-aware cache cleanup
- Added test coverage for `cache_manager.py` (9 tests)

### Fixed

- Fix clutter grid ownership: user-provided land-cover rasters are no longer closed by the algorithm after use (auto-downloaded grids are still cleaned up)
- Fix duplicated numpy scans in coverage report display — statistics are now read from the precomputed report payload
- Fix missing `from __future__ import annotations` in `elevation.py` for Python 3.9 compatibility
- Fix coverage pool module-level globals: removed unused `_cov_pool_id`/`_cov_pools` dead code, replaced with concise comment
- Fix unused `rx_sens` parameter in `write_coverage_raster()` — parameter removed from signature and call sites
- Fix duplicate imports in `clear_dem_cache()` function body
- Fix unused `QMessageBox` import in `nowires.py`
- Fix `algorithm_contour.py`: added fallback when `get_temp_dir()` returns None
- Fix `comparison_add_params.py`: extracted `_add_panel_advanced_params()` helper to keep file under 300-line limit
- Fix `coverage_pool.py`: made `_MAX_WORKERS` computation lazy via `_get_max_workers()` function
- Fix misleading test name `test_handles_broken_symlinks` renamed to `test_handles_readonly_files`

- Fix Qt6 crash when toggling obstruction visibility in P2P chart (Windows access violation)
- Fix Coverage Comparison silently ignoring advanced clutter controls (percentile, street width, BEL, building type, elevation angle)
- Fix P2P output geometries drawn wrong across the antimeridian (±180°)
- Fix `_owns_clutter` UnboundLocalError masking real DEM errors in coverage algorithm
- Fix coverage TX marker not persisting across QGIS sessions — now uses fixed path under user temp dir
- Fix P2P output layers (profile, fresnel, markers) not persisting across QGIS sessions
- Add `_vector_layer_ids` initialization to CoverageAlgorithm for proper layer reordering
- Add `get_temp_dir` stub to P2P compute test for dem_downloader mock
- Defensive `len()` for QGIS layer tree children in base_algorithm

### Changed

- `.gitignore`: added `.coverage` to tracked patterns
- Persistent output paths: coverage and P2P layers now write to fixed directory under user temp dir


## [1.5.0] - 2026-05-07

### Added

- Added "Advanced clutter correction" mode: saalos vegetation model, ITU-R P.2108 for built/rural categories
- Added saalos vegetation clutter model (Python port of ITWOM 3.0 ClutterLoss by Sid Shumate, via the MIT-licensed clutterloss-itm Rust crate). See NOTICE.md for the full MIT license text.
- Added ITU-R P.2108-1 §3.2 statistical clutter loss for terrestrial paths (combined urban+suburban model, 0.5–67 GHz, percentile-based, distance-capped at 2 km)
- Added ITU-R P.2108-1 §3.1 height-gain terminal correction (per-category, 0.03–3 GHz, methods 2a/2b)
- Added ITU-R P.2109-2 building entry loss (two-lognormal model with elevation angle, per building type)
- Added per-category model dispatch per the P.2108/P.2109 compliance design: `none` (open), `p2108_height_gain` (open_rural, dense_rural), `saalos` (vegetation), `p2108_combined` (suburban, urban with §3.1+§3.2 overlap max)
- Added `CLUTTER_PERCENTILE` parameter (0.01–99.99) for P.2108 §3.2 and P.2109 BEL
- Added `STREET_WIDTH_M` parameter (5–100 m, default 27) for P.2108 §3.1
- Added `BEL_ENABLED` boolean parameter for P.2109 building entry loss
- Added `BEL_BUILDING_TYPE` enum (Traditional / Thermally-efficient) for P.2109
- Added `BEL_ELEVATION_ANGLE` parameter (0–90°, default 0) for P.2109
- Added `method`, `percentile`, `tx_bel_db`, `rx_bel_db`, `total_with_bel_db` fields to `TerminalClutterLosses`
- Added `p2108_common.py` — shared Q⁻¹ and F⁻¹ inverse normal CDF implementations with sign-convention guard tests
- Added `p2108_height_gain.py` — P.2108-1 §3.1 height-gain terminal correction (scalar + vectorized)
- Added `p2108_terrestrial_stat.py` — P.2108-1 §3.2 statistical clutter loss (scalar + vectorized)
- Added `p2109_bel.py` — P.2109-2 building entry loss (scalar + vectorized)
- Added `R_m`, `p2108_3_1_method`, `p2108_3_2_applicable` fields to `CLUTTER_CATEGORY_PARAMS`
- Added `percentile`, `street_width_m`, `bel_enabled`, `bel_building_type`, `bel_elevation_angle_deg` to `ClutterLossContext`
- Added `clutter_method` and `clutter_percentile` to P2P report payload
- Added `bel_rx_db` to P2P report payload
- Added `clutter_method` field to `TerminalClutterLosses` for reporting which sub-model fired (e.g. `"§3.1+§3.2/saalos"`)
- Added total path loss computation including BEL: `total_with_bel_db = total_loss_db + rx_bel_db`
- Added comprehensive test suites for p2108_common (24 tests), p2108_terrestrial_stat (14), p2108_height_gain (14), p2109_bel (10)

### Changed

- **Breaking**: Replaced the simplified per-category `clutter_loss_p2108` with proper ITU-R P.2108-1 §3.2 statistical model. Urban/suburban clutter loss values will differ significantly from the previous approximation (which was incorrect).
- **Breaking**: `CLUTTER_CATEGORY_PARAMS` no longer has `base_loss_db` or `model="p2108"`. Use `R_m`, `p2108_3_1_method`, `p2108_3_2_applicable`, and `model="p2108_height_gain"` / `"p2108_combined"` instead.
- P2P analysis now passes `ClutterLossContext` to the advanced clutter dispatch, including antenna height, distance, frequency, and polarization for saalos and P.2108
- P2P total path loss now uses `total_with_bel_db` (includes BEL when enabled)
- Coverage engine caches the TX terminal clutter loss and reuses it across all coverage pixels when using advanced mode
- Coverage per-pixel loop now adds P.2109 building entry loss to RX clutter when `BEL_ENABLED=True`
- Batch and comparison workflows now propagate advanced clutter context and canopy height overrides through their parameter pipelines
- `clutter_p2108.py` is now a deprecation shim that delegates to `p2108_terrestrial_stat` with a `DeprecationWarning`
- Advanced clutter mode now dispatches per-category per-frequency per §6 of the compliance design:
  - open → 0 dB
  - open_rural / dense_rural → P.2108 §3.1 height-gain (f < 3 GHz)
  - vegetation → SAALOS (unchanged)
  - suburban / urban → P.2108 §3.1 + §3.2 combined (max of both in 0.5–3 GHz overlap; §3.2 only above 3 GHz)
- Coverage comparison now propagates BEL parameters through its parameter pipeline

### Fixed

- Fix `ModuleNotFoundError: No module named 'clutter_constants'` at QGIS runtime — `clutter_saalos.py` used absolute import instead of package-relative import
- Fix coverage heatmap missing color near transmitter — palette had no stop above -60 dBm, so strong-signal pixels (> -60 dBm) rendered as transparent in Discrete shader mode. Added "Very Strong" (-30 dBm) stop and a +100 dBm ceiling entry so values up to +100 dBm are covered by the Very Strong color interval.
- Fix P2P owned clutter grid not closed after sampling, preventing GDAL dataset handle leak
- Fix TOCTOU race conditions in temp directory creation
- Fix four stale contract tests that diverged from actual implementation
- Remove four unused imports flagged by ruff
- Fix GDAL handle leak in coverage shared clutter grid cleanup
- Fix NaN dedup logic in coverage summary
- Add safety net `__del__` handlers in `temp_manager.py` and `nan_utils.py` for resource cleanup
- Fix macOS multiprocessing compatibility: prevent duplicate QGIS windows and fix Python executable path
- Fix P.2108 frequency factor: unify all categories to use the same diffraction-based scaling where clutter loss increases with frequency, consistent with P.2108-1 §3.1 Eq. (2f) and §3.2
- Fix coverage pool falling back to sequential mode on worker errors instead of propagating exceptions
- Fix duplicate `compute_terminal_clutter_losses` call in coverage pipeline
- Fix ElevationGrid edge-registered pixel offset and dead globals cleanup
- Fix import of `fresnel_profile_analysis` from `fresnel` module instead of `radio`
- Fix string constant names in comparison `add_clutter_params` instead of `getattr`
- Fix 14 code review issues: resource leaks, metric consistency, API correctness
- Comprehensive macOS compatibility fixes for multiprocessing and GUI

## [1.4.0] - 2026-05-03

### Added

- Batch P2P Analysis algorithm: one-to-many and many-to-one link computation, results ranked by link margin, with combined output layer and optional CSV export
- Coverage Comparison algorithm: dual-panel coverage analysis producing a delta raster (Panel A – Panel B in dB) with statistics and optional report
- Interactive P2P profile chart with hover callouts, Fresnel zone toggle, and chart export
- P2P report and marker outputs (vector layers for TX/RX markers)
- Coverage report outputs (CSV/JSON/HTML)
- Reliability outputs: fade-margin classes, formal-or-fallback availability guidance in P2P and coverage reports
- Live coverage opacity slider dialog (plugin menu action)
- 3D scene tracking and opening for coverage and contour outputs (disabled on Windows)
- P2P rule-based symbology for Fresnel zone, line, and profile layer outputs
- Shared parameter registration (`shared_params.py`), shared DEM grid management (`shared_dem_grid.py`)
- Shared GeoTIFF writer (`raster_io.py`)
- macOS multiprocessing compatibility (`macos_compat.py`)
- NaN-safe array utilities (`nan_utils.py`)
- Temp directory manager with cleanup safety net (`temp_manager.py`)

### Changed

- Architecture refactor: algorithm files split from monoliths over 1000 lines into focused helper modules (coverage, contour, batch, p2p)
- Coverage helper code split by responsibility: `coverage_compute.py`, `coverage_palette.py`, `coverage_legend.py`, `coverage_summary.py`, `coverage_reporting.py`, `coverage_analysis_params.py`
- Contour code split: `contour_generation.py`, `contour_overlay.py`, `contour_pipeline.py`, `contour_smoothing.py`, `contour_symbology.py`
- P2P code split: `p2p_analysis_params.py`, `p2p_params.py`, `p2p_compute.py`, `p2p_outputs.py`, `p2p_chart.py`, `p2p_chart_format.py`, `p2p_symbology.py`, `p2p_report_display.py`
- Comparison code split: `comparison_add_params.py`, `comparison_params.py`, `comparison_panel.py`, `comparison_outputs.py`, `comparison_reporting.py`
- Batch code split: `batch_analysis_params.py`, `batch_params.py`, `batch_outputs.py`, `batch_writer.py`
- Clutter code split: `clutter.py`, `clutter_advanced.py`, `clutter_categories.py`, `clutter_constants.py`, `clutter_context.py`, `clutter_p2108.py`, `clutter_saalos.py`
- Constants extracted into `constants.py` and `defaults.py`
- Base algorithm class extracted into `base_algorithm.py`
- P2P batch constant registration collapsed into dict comprehension
- Comparison panel constants auto-generated in `comparison_params.py`

### Fixed

- **CR3**: Fix VRT Gaussian smoothing being a silent no-op. `root.iter("Source")` never matched `SimpleSource`/`ComplexSource` tags, so the Gaussian kernel was never injected into the VRT. Contour smoothing now works as intended.
- **CR4**: Fix comparison delta math: add COVERAGE_NODATA→NaN normalization and shape guard in `compute_delta_summary` to prevent -9999 sentinel values from being treated as real data.
- **CR5**: Move `QgsProject.instance().writeEntry` calls from `processAlgorithm` to `postProcessAlgorithm` in `base_algorithm.py` to avoid mutating project state inside the processing algorithm.
- **CR6**: Remove dead `_cleanup_cov_pool` function; cap `n_workers` at `_MAX_WORKERS` (16) in coverage engine.
- **CR7**: Fix `unload()` AttributeError by initializing `_toolbar_actions` and `_opacity_dialog` in `__init__`; add `getattr` guards for action removal.
- **CR8**: Fix URL redirect validation from substring prefix check (`startswith`) to `urlsplit().netloc` comparison to prevent URL spoofing.
- Fix FSPL constant: `32.44` → `32.45` in `p2p_compute.py` to match ITU-R P.525 and the ITM internal constant.
- Add RX cable loss to received power calculation (was only subtracted at TX).
- Add NaN count warning in coverage pool worker when replacing NaN elevations with 0.0.
- Change `itm_p2p_loss` exception sentinel from `999.0` to `NaN` with `failed=True` flag to prevent downstream calculations from treating failures as real values.
- Fix CSV injection in report export: sanitize cell values starting with `=`, `+`, `-`, `@`, tab, or CR.
- Fix JSON NaN output in report export: sanitize NaN/Inf values before `json.dump` with `allow_nan=False`.
- Fix copy-paste defaults: `LOCATION_PCT` and `SITUATION_PCT` now use `DEFAULT_LOCATION_PCT` and `DEFAULT_SITUATION_PCT` instead of `DEFAULT_TIME_PCT` in batch params, comparison params, and P2P params.
- Fix `_feat_attr` boolean-vs-int dispatch: check `isinstance(default, bool)` before `isinstance(default, int)`.
- Add `super().unload()` call in `NoWiresProvider.unload()`.
- Fix comparison reporting: return NaN percentages instead of misleading 0.0% when valid_count is zero.
- Add `pushWarning` with error summary when raster layers are invalid in coverage and comparison algorithms.
- Initialize `clutter_grid = None` before try block in `algorithm_coverage.py` to prevent `UnboundLocalError`.
- Fix `gdal.Translate` NoData remap: use `gdal.Warp` with `srcNodata`/`dstNodata` when source NoData differs from target, preventing -9999 elevations from dominating Gaussian blur.
- Add `COVERAGE_NODATA` normalization in `coverage_summary.py` to handle reloaded GeoTIFFs.
- Add `f.flush()` + `os.fsync()` before `os.replace()` in tile download to prevent torn files on power loss.
- Add temp directory permission check in `dem_downloader.py` after `os.makedirs`.
- **Note on NC1/NC2**: Verified as correct behavior, not bugs — the ITM smooth-earth fallback sign and polarization branch both match the NTIA reference implementation.

## [1.3.0]

### Added

- Antenna presets (omni, sector 90/120, dish 20, custom), front-to-back ratio, downtilt, and optional horizontal/vertical pattern CSV support for both P2P and coverage workflows.
- Optional simple terminal clutter correction with WorldCover-style land-cover sampling; clutter loss components (`clutter_tx_db`, `clutter_rx_db`, `total_path_loss_db`) are now visible in all report payloads.
- `worldcover_downloader.py`: ESA WorldCover 2020 v100 tile download, caching, and clip/merge (mirrors the DEM downloader pattern).
- `clutter_source_label()` helper for descriptive clutter source labels in reports.
- `compute_terminal_clutter_losses()` helper for consistent terminal clutter loss computation.
- Coverage report payloads now include `itm_loss_db`, `clutter_tx_db`, `clutter_rx_db`, and `total_path_loss_db` fields.
- P2P clutter grid download now occurs after the bounding box is computed, ensuring the correct area is covered.

### Changed

- Clutter source in P2P and coverage reports is now produced by `clutter_source_label()` instead of a raw file path or inline conditional.
- Coverage clutter reporting now uses the TX terminal clutter loss as the representative `clutter_tx_db` and derives `clutter_rx_db` from the grid-wide mean totals.

### Removed

- The obsolete Qt compatibility helper module has been removed; source now uses QGIS 4 / Qt 6 APIs directly.

### Fixed

- **NC1**: Guard `smooth_earth_diffraction` and `height_function` against `ValueError` from `log`/`log10` on non-positive arguments. When low frequency × small ground impedance causes `K > 1.607`, `B_0` can go negative, which previously crashed the ITM prediction for vertical polarization at 20 MHz over high-conductivity ground. Now returns a large finite loss value consistent with the extreme diffraction regime.
- **NC2**: Add per-task exception handling in `_itm_worker_batch` so a single bad pixel no longer kills an entire chunk of coverage tasks. Broaden the `ProcessPoolExecutor` fallback `except` clause from specific exception types to `Exception`, so `ValueError` and `TypeError` also trigger the sequential fallback with diagnostic logging.
- **NI1**: Add a shared `multiprocessing.Event` for cancellation signalling between the coverage engine and worker processes, reducing cancellation latency from chunk-sized (5–50 s) to task-sized.
- **NI2**: Add `_final_cov_pool()` to close per-worker shared-memory handles on pool shutdown, preventing resource leaks on platforms where OS cleanup is not immediate.
- **NI3**: Extract the -9999 NoData sentinel into a named constant `COVERAGE_NODATA` with documentation explaining why NaN is not used (GDAL Float32 compatibility) and why -9999 is safe.
- **NI4**: Remove unused `TYPE` field from the contour line layer in `algorithm_contour.py`; `gdal.ContourGenerate` never populates it and no downstream code references it.
- **NI5**: Fix `_feat_attr` silent type coercion in `algorithm_batch.py`. `int(float(val))` now logs a warning on truncation, and coercion failures log the attribute name, value, and target type instead of silently falling back to the default.
- **NI6**: Both DEM and WorldCover downloaders now honour the HTTP `Retry-After` header on 429/503 responses, using the server-suggested wait time instead of fixed exponential backoff.
- **NI7**: Socket timeout values in both downloaders extracted into named constants (`_SOCKET_TIMEOUT`) for visibility. A `_WALL_CLOCK_TIMEOUT` constant documents the intended total-per-tile timeout as a contract for future enforcement.
- **NM9**: Add 38 ITM reference-vector tests covering `smooth_earth_diffraction` edge cases (NC1 regression), propagation primitives, and end-to-end `predict_p2p` scenarios across all climate zones, boundary frequencies, and polarization modes.
- Fix Qt 6 `QAction` import location and keep source checks for direct Qt 6 enum usage.
- Fix P2P clutter grid download bounding box: WorldCover tiles are now fetched after the padded TX–RX extent is known, preventing zero-area downloads when the TX and RX are close together.

## [1.2.0]

- Remove `gdal_calc.py` (dead code with `eval()` usage and deprecated `optparse`).
- Fix critical import bug in `report_payloads.py` — bare `from reliability import` would crash at QGIS runtime.
- Vectorize `coverage_summary.py` distance computation for significant speedup on large grids.
- Replace fragile VRT string manipulation in `algorithm_contour.py` with proper XML parsing.
- Use namedtuples for coverage task tuples to prevent fragile positional unpacking.
- Remove global GDAL configuration side effects from `dem_downloader.py` that affected the entire QGIS process.
- Use `NaN` instead of `0.0` for nodata replacement in `ElevationGrid` to distinguish nodata from sea level.
- Remove legacy `sys.path` manipulation from `nowires.py` and `coverage_engine.py`.
- Fix import ordering violations and remove unused imports across multiple files.
- Normalize copyright headers to consistent `(C) 2026 by Bortre Tenamo`.
- Extract magic numbers into named constants for clarity.
- Remove redundant `sys.path` insertions from test files.
- Prepare repository for public GitHub upload.
- Split coverage helpers into `coverage_compute.py` and `coverage_colors.py`.
- Add a synthetic coverage runtime benchmark under `benchmarks/coverage_runtime.py`.
- Add a live `Coverage Opacity` plugin action for the latest coverage layer.
- Restore tracked 3D scene support for coverage and contour outputs.
- Disable plugin-launched 3D canvas creation on Windows and defer to the native QGIS 3D view workflow there.
- Add CSV, JSON, and HTML report export for P2P and coverage workflows.
- Add TX/RX marker output for point-to-point analysis.
- Add reliability outputs and availability estimates for P2P and coverage reports.
- Improve the Windows 3D fallback guidance for opening the native QGIS 3D view.
- Fix coverage raster cell-center alignment so the heatmap matches the requested map extent.
- Fix DEM north-up sampling so coverage and terrain-derived outputs are not mirrored upside down.
- Fix Windows access violation crash caused by `QgsProject.instance().addMapLayer()` called from inside `processAlgorithm`.
- Fix "layer not correctly generated" error by replacing `RasterDestination`/`VectorDestination` output parameters with `FileDestination` to prevent double-loading conflict with manually queued styled layers.
- Fix DEM raster layers loading on top of coverage/contour outputs; `postProcessAlgorithm` now moves DEM layers to the bottom of the layer tree.
- Fix missing `ANTENNA_AZ` class constant that caused `AttributeError` at algorithm initialization.

## [1.1.0]

- Replace separate area coverage and radius sweep workflows with unified `Coverage Analysis`.
- Add raster-derived coverage range statistics.
- Improve coverage raster styling and controls.
- Add regression coverage for Processing contracts and coverage behavior.
