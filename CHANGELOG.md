# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] - 2026-05-07

### Added

- Added "Advanced clutter correction" mode: saalos vegetation model, ITU-R P.2108 for built/rural categories
- Added saalos vegetation clutter model (Python port of ITWOM 3.0 ClutterLoss by Sid Shumate, via the MIT-licensed clutterloss-itm Rust crate). See THIRD_PARTY_NOTICES.md.
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
