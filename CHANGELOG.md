# Changelog

SPDX-License-Identifier: GPL-3.0-or-later

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.8] - 2026-05-17

### Changed

- Decompose `coverage_pool.py` (300→276 lines): extract `apply_batch_results` and `log_coverage_failures` into `_coverage_result_dispatch.py`.
- Decompose `p2p_compute.py` (300→265 lines): extract `_write_p2p_output_layers` and `_write_p2p_reports` into `_p2p_outputs_internal.py`.
- Decompose `contour_smoothing.py` (300→195 lines): extract Gaussian kernel, raster calc, and blur VRT helpers into `_smoothing_vrt.py`.
- Replace hardcoded `111320.0` in `algorithm_coverage.py` and `algorithm_coverage_comparison.py` with `METERS_PER_DEGREE_LAT` from `constants.py`.
- Replace `f_mhz: float = 300.0` defaults in `CoverageAnalysisParams` and `BatchAnalysisParams` with `DEFAULT_FREQ_MHZ` from `defaults.py`.
- Replace `N0=301.0, epsilon=15.0, sigma=0.005` in `coverage_engine.compute_coverage` with `DEFAULT_N0`, `DEFAULT_EPSILON`, `DEFAULT_SIGMA` from `defaults.py`.
- Add `SMOOTHING_NONE`, `SMOOTHING_LOW`, `SMOOTHING_MEDIUM`, `SMOOTHING_HIGH`, `SMOOTHING_OPTIONS` constants in `contour_smoothing.py`; replace string literals in `algorithm_contour.py` parameter registration.
- Add `DELTA_STYLE_DIVERGING` and `DELTA_STYLE_THRESHOLD` constants in `comparison_params.py`; replace string literals in `comparison_outputs.py`.
- Add `CLUTTER_OVERRIDE_AUTO` constant in `clutter.py`; replace `"Auto"` string comparisons.
- Collapse `SharedDEMGrid._atexit_cleanup` into class-level alias on `release`; eliminates duplicate logic.
- Convert silent `except … pass` in `shared_dem_grid.py` close/release/unlink paths to `logger.debug`; narrow `except Exception` to `except OSError`.
- Drop duplicate `ProcessPoolExecutor` re-export from `coverage_engine.py`; all runtime usage and monkeypatching lives in `_coverage_executor.py`.
- Add `gdal_integration` pytest marker for tests that require numpy-2-compatible GDAL bindings; exclude from host unit-test run, include in QGIS Docker integration run.
- Add `WGS84_CRS` singleton to `constants.py`; replace 6 inline `QgsCoordinateReferenceSystem("EPSG:4326")` constructions across `algorithm_p2p`, `algorithm_batch`, `algorithm_contour`, `algorithm_coverage_comparison`, `comparison_panel`, `coverage_params`.
- Move `FRESNEL_60PCT_FACTOR` from `defaults.py` to `constants.py`; update import sites in `fresnel.py`, `p2p_outputs.py`, `p2p_chart.py`.
- Add `EMPTY_MARGIN_DB = -999.0` to `constants.py`; replace magic literal in `report_payloads.py`.
- Replace 3 hardcoded `1048576.0` literals in `nowires.py` and `cache_manager.py` with `BYTES_PER_MEBIBYTE` from `constants.py`.
- Convert remaining 7 silent `except … pass` sites to `logger.debug`: `nowires.py` (3 sites), `three_d.py`, `p2p_chart.py`, `temp_manager.py`, `processing_utils.py`. Narrow `except Exception` to `except OSError` where safe (shared memory, temp dir).
- Add `from __future__ import annotations` to 7 clutter/p2108 modules (`clutter_categories`, `clutter_constants`, `clutter_resolve`, `clutter_saalos`, `p2108_common`, `p2108_terrestrial_stat`, `p2109_bel`) for consistency with sibling modules.
- Replace `last_contour_layer_id` string literal at `three_d.py:79` with `CONTOUR_LAYER_KEY` constant.
- Reconcile sequential-mode notice in `_coverage_executor.py` with MP-fallback message: `"Using single-threaded mode..."` → `"Single-threaded mode: no multiprocessing detected"`.
- Replace `# type: ignore[arg-type]` cluster in `comparison_reporting.py` with explicit `assert tmpdir is not None`; removes three type-ignore suppressions.
- Break `clutter.py` ↔ `clutter_advanced.py` import cycle: move `TerminalClutterLosses` from `clutter.py` to `clutter_context.py`, eliminating the deferred-import workaround.
- Extract a single shared bilinear sampler into `_bilinear.py` (`bilinear_sample`, `bilinear_sample_grid`, `bilinear_sample_grid`), consolidating four re-implementations in `ElevationGrid.sample`, `ElevationGrid.sample_line`, `ElevationGrid.sample_grid`, and `sample_line_from_grid`.
- Promote underscore-private clutter symbols to public API: `_ClutterComponents` → `ClutterComponents`, `_compute_advanced_loss` → `compute_advanced_loss`, `_resolve_category_advanced` → `resolve_category_advanced`; move `legacy_to_advanced_override` from `clutter_resolve.py` to `clutter_categories.py`.
- Improve `worldcover_class_to_clutter_category` out-of-range handling: early-return `"open"` for invalid class IDs instead of `% 256` fallthrough.
- Wrap `document.print(printer)` in `report_pdf.write_report_pdf` in try/except with `logger.debug` and `return False` on failure.
- Add module description to `nowires.py`.
- Single-source per-category P.2108 parameters: derive `p2108_height_gain._CATEGORY_PARAMS` from `clutter_categories.CLUTTER_CATEGORY_PARAMS` instead of duplicating `R_m` and method tags.
- Convert stringly-typed enums to `typing.Literal`: add `ClutterModel = Literal["simple", "advanced"]` and `BuildingType = Literal["traditional", "thermally_efficient"]` in `clutter_context.py`; update type annotations across all call sites.
- Replace length-tag dispatch `isinstance(result, tuple) and len(result) == 2 and result[0] == "error"` in `_coverage_result_dispatch.py` with `WorkerError` frozen dataclass sentinel.
- Move `_warned_low_vhf_p2108_combined` global mutable flag into `_P2108State` dataclass in `clutter_resolve.py`; tests can reset via `_STATE.warned_low_vhf = False`.

### Added

- Added `test_p2108_category_params_derived_from_clutter_categories.py` — consistency test verifying `_CATEGORY_PARAMS` in `p2108_height_gain` is derived from `CLUTTER_CATEGORY_PARAMS`.
- Added `test_worker_error_sentinel.py` — regression test for `WorkerError` dataclass sentinel replacing length-tag dispatch.

### Deferred
### Added

## [1.5.7] - 2026-05-17

### Fixed

- Fix haversine numerical stability in `coverage_summary._compute_grid_summary` — add `a = np.clip(a, 0.0, 1.0)` before `2 * R * np.arcsin(np.sqrt(a))` so FP rounding at antipodal or near-zero distances no longer yields NaN distances.
- Replace `assert self.data is not None` with `RuntimeError` in `ElevationGrid.sample`, `sample_line`, and `sample_grid`. `assert` is a no-op under `python -O`; an explicit raise is always enforced and much easier to diagnose than a silent NaN read after `close()`.
- Fix `algorithm_batch.processAlgorithm` unconditionally closing the user-supplied clutter grid. Add `owns_clutter_grid` flag to `BatchAnalysisParams` and `_collect_batch_inputs` (set True only when auto-downloaded); gate the close in `processAlgorithm` on that flag, mirroring `p2p_compute.py:133-137,294-298`.
- Fix `coverage_pool._init_cov_pool` re-registering `_final_cov_pool` on every initializer call. Gate `atexit.register` with a module-level `_cov_pool_atexit_registered` flag so the finalizer is registered exactly once even across worker reinit.
- Fix `_coverage_executor.execute_coverage_tasks` discarding partial multiprocessing counters when the pool raises and falls back to sequential. Accumulate (`pixels_failed += seq_failed`, `pixels_done += seq_done`) rather than reassign.
- Fix GDAL dataset leak in `contour_pipeline.download_and_merge_tiles` clip verification. Replace bare `gdal.Open(fn_clip) is None` with explicit `test_ds = gdal.Open(fn_clip); ...; test_ds = None` pattern matching `tile_download_base.py:143-154`.
- Fix `NoWiresPlugin.run_pattern_preview` antenna-preview dialog leak. Declare `_pattern_preview_dialog = None` in `__init__`, close-then-replace on each invocation, and close in `unload()` — mirroring the `_opacity_dialog` lifecycle.
- Clamp `geo_bounds.coverage_bounds` results to valid lat range `[-90, 90]` and replace local `meters_per_deg_lat = 111320.0` with `METERS_PER_DEGREE_LAT` from `constants.py`.
- Fix `coverage_params._add_pct_params` using `DEFAULT_TIME_PCT` for all three percentage parameters. Split the loop so each `addParameter` call references its matching default (`DEFAULT_TIME_PCT`, `DEFAULT_LOCATION_PCT`, `DEFAULT_SITUATION_PCT`).
- Fix `contour_overlay.py:103-106` releasing hillshade dataset without flushing pyramid overviews. Add `hillshade_ds.FlushCache()` before `hillshade_ds = None`.
- Fix `algorithm_contour.py:96-97` leaking permanent temp directory when `get_temp_dir()` returns None. Route the fallback `tempfile.mkdtemp` through `TempDirManager.add_dir` for cleanup.
- Fix `ElevationGrid.__init__` zero-division on degenerate DEM rasters. Raise `RuntimeError` when `n_rows == 0` or `n_cols == 0` before computing `d_lat` / `d_lon`.
- Fix `summarize_coverage_grid` zero-division on empty grids. Return the zero-count summary dict early when `n_rows == 0` or `n_cols == 0`.
- Fix `SharedDEMGrid._create` atexit-handler pinning `self` and `shm`. Replace bound-method `atexit.register(self._atexit_cleanup)` with module-level `_pending_releases` weak-reference dict and `_atexit_release_pending` handler; add `__del__` safety-net so abandoned segments are released promptly.

### Added

- Added `test_haversine_clip.py` — regression test for haversine numerical stability.
- Added `test_elevation_runtime_error.py` — regression test for `assert` → `RuntimeError` in ElevationGrid.
- Added `test_batch_owns_clutter_grid.py` — regression test for batch clutter-grid ownership flag.
- Added `test_pool_atexit_gating.py` — regression test for atexit re-registration gating.
- Added `test_executor_partial_counters.py` — regression test for partial counter accumulation on MP fallback.
- Added `test_contour_pipeline_clip_leak.py` — regression test for GDAL dataset leak in clip verification.
- Added `test_pattern_preview_dialog_leak.py` — regression test for antenna-preview dialog lifecycle.
- Added `test_hillshade_flush_cache.py` — regression test for FlushCache before hillshade release.
- Added `test_contour_tempdir_cleanup.py` — regression test for fallback temp-dir cleanup registration.
- Added `test_shared_dem_atexit_weakref.py` — regression test for weak-reference atexit registry in SharedDEMGrid.
- Added `test_geo_bounds_lat_clamp.py` — regression test for lat clamping and METERS_PER_DEGREE_LAT import.
- Added `test_elevation_zero_div_guard.py` — regression test for zero-rows/cols RuntimeError guard.
- Added `test_coverage_summary_zero_div_guard.py` — regression test for empty-grid zero-division guard.
- Added `test_coverage_pct_param_defaults.py` — regression test for separate percentage parameter defaults.

## [Unreleased]

### Planned (PATCH — tech-debt / cleanup, zero behavior change)

- Bundle parameter explosion into frozen dataclasses. `compute_coverage` carries 35 params, `build_p2p_report_payload` carries 35, `build_coverage_report_payload_for_grid` carries 31. Most natural groupings (`AntennaConfig`, clutter bundle, link budget, BEL settings) already exist; the work is wiring them through.
- Decompose three long functions: `run_p2p_analysis` (183 lines), `_compute_single_link` (158 lines), `run_panel_coverage` (232 lines).
- Re-examine the tile-cache validation in `tile_download_base.download_tile_with_retry`. Any `ComputeStatistics` failure on a cached file is treated as corruption — consider validating only structural integrity on cache hits.
- Reconsider the overall wall-clock deadline in `dem_downloader.download_tiles`. Either drop the overall deadline or scale it with tile count.

### Planned for v1.6.0  (MINOR — additive features)

- Extend PDF report output (`OUTPUT_REPORT_PDF`) from Coverage Analysis to Point-to-Point Analysis and Coverage Comparison. The shared `report_pdf.write_report_pdf()` writer is already in place; remaining work is parameter registration and `_write_*_outputs` wiring in `algorithm_p2p` and `algorithm_coverage_comparison`.
- Promote the standalone "Preview Antenna Pattern" dialog into an inline `QgsProcessingParameterWidgetFactoryInterface` so the polar plot renders directly in the Coverage / P2P parameter dialog next to the pattern-file picker.
- Audit `report_pdf.write_report_pdf()` for paged-table behaviour on long reports — current implementation lets `QTextDocument` decide page breaks. Resolve before or during PDF parity work.

## [1.5.6] - 2026-05-17

### Fixed

- Fixed `_pickle.PicklingError: Can't pickle <function _init_cov_pool at 0x...>: it's not the same object as NoWires.coverage_pool._init_cov_pool` on Windows multiprocessing. The error surfaced on Windows after the v1.5.5 `pythonw.exe` switch made `find_windows_python_executable()` succeed where it had been silently returning `None` on user setups — so the multiprocessing branch ran for the first time and exposed a latent bug.

  Root cause: `_coverage_executor.py` did `from .coverage_pool import _init_cov_pool, _itm_worker_batch` at module-import time, freezing those names as references to the function objects from the *first* import of `coverage_pool`. If anything subsequently replaced `NoWires.coverage_pool` in `sys.modules` — QGIS plugin reload, the "Plugin Reloader" plugin, any manual `importlib.reload` of just that one file — `sys.modules["NoWires.coverage_pool"]._init_cov_pool` became a new function object, but `_coverage_executor._init_cov_pool` still pointed at the old one. `pickle`'s identity check (`getattr(sys.modules[fn.__module__], fn.__qualname__) is fn`) then failed when `ProcessPoolExecutor` tried to serialize the initializer to send to the spawned worker.

  Fix: resolve both `_init_cov_pool` and `_itm_worker_batch` through `from . import coverage_pool as _cp` *inside* `execute_coverage_tasks`, so each call walks `sys.modules` fresh and the function references handed to `ProcessPoolExecutor` are guaranteed identical to what `pickle` finds by name. The module-level `from .coverage_pool import ...` line no longer carries those two names.

### Changed

- Changed the multiprocessing-fallback diagnostic in `_coverage_executor.execute_coverage_tasks` from `feedback.pushInfo("Multiprocessing unavailable, using single-threaded mode...")` to `feedback.pushWarning("Multiprocessing unavailable ({}: {}), using single-threaded mode...".format(type(exc).__name__, exc))`. Previously, when the MP branch raised, the exception type and message were emitted only via Python `logger.warning`; on GUI-subsystem QGIS builds (Windows `pythonw.exe`-bundled, some macOS configurations) the `StreamHandler` can have `stream=None` and silently drop the message — leaving the user with an opaque "Multiprocessing unavailable" with no trail back to the underlying cause. Routing the exception details through the QGIS Processing feedback channel keeps future regressions self-diagnosing in the log panel.

### Added

- Added `tests/test_coverage_executor_reload_pickle.py` — three regression tests that lock in the lazy-lookup contract: (1) after `importlib.reload(coverage_pool)`, the function objects passed to a fake `ProcessPoolExecutor` must be `is`-identical to the reloaded module's attributes; (2) `pickle.dumps` on the reloaded `_init_cov_pool` / `_itm_worker_batch` must succeed (mirrors what `ProcessPoolExecutor` does on spawn); (3) source-level check that `_coverage_executor.py` does not import either symbol at module scope ahead of `execute_coverage_tasks`. Verified the first and third fail without the fix and pass with it.

### Documentation

- `Technical_Documentation.md`: expanded the "Multiprocessing in QGIS" and "Coverage Engine Robustness" sections with the function-local-import contract, the underlying pickle identity-check failure mode, and how v1.5.5's `pythonw.exe` detection unmasked the previously-latent bug on Windows.

## [1.5.5] - 2026-05-16

### Fixed

- Fixed coverage multiprocessing silently falling back to sequential mode on macOS via **three distinct bugs** that all surfaced as `feedback.pushInfo("Multiprocessing unavailable, using single-threaded mode...")` with the actual exception logged only via Python `logger.warning` (often invisible in the QGIS UI).

  **(1) macOS POSIX shared-memory name too long.** `shared_dem_grid.SharedDEMGrid._create()` was generating names of the form `nowires_dem_<20 hex>` (32 chars). macOS XNU defines `PSHMNAMLEN = 31` as the maximum length including the leading `/` that `multiprocessing.shared_memory.SharedMemory` prepends, so the actual limit after the slash is 30 chars. Names of 32 chars + leading slash = 33 chars triggered `OSError: [Errno 63] File name too long` at `SharedMemory(create=True, name=...)`. Linux's `NAME_MAX = 255` hid this. Fix: truncate the UUID hex suffix from 20 to 16 chars (28 chars total, 29 with slash; comfortably under the macOS limit).

  **(2) Spawn-mode cross-process cancel signal abandoned.** Even with the shm name fix, the next step in the pipeline used a plain `multiprocessing.Event()` in `_coverage_executor.execute_coverage_tasks`. Under the `spawn` start method (macOS default, Windows, containers), the Event's internal Condition raises `RuntimeError: Condition objects should only be shared between processes through inheritance` when `pool.map` tries to pickle it. An interim fix using `multiprocessing.Manager().Event()` worked in Docker but died on the user's macOS QGIS with `EOFError` (the Manager subprocess couldn't be sustained in that environment). The fix that actually works: **remove the cross-process cancel signal entirely**. Cancellation now comes from the main thread breaking out of `pool.map` between batches; in-flight batches finish naturally (~64 tasks × ~5 ms ≈ 320 ms worst case at default chunk size). Linux `fork` was masking both issues.

  **(3) QGIS-bundled `python3.12` aborts on spawn because `sys.prefix` is baked to a CI-builder path.** After (1) and (2) were fixed, workers started spawning but died immediately with `ModuleNotFoundError: No module named 'encodings'` and `Fatal Python error: init_fs_encoding: failed to get the Python codec of the filesystem encoding`. The macOS QGIS-final 4.0.2 build ships a `python3.12` binary whose `sys.prefix` is hard-coded to `/Users/runner/work/QGIS/QGIS/build/vcpkg_installed/arm64-osx-dynamic-release/` (the CI builder's path). QGIS itself overrides this internally via `Py_SetPythonHome()`, but spawned children get no such override and can't find the stdlib. Surfaced as `BrokenProcessPool: A child process terminated abruptly`. Fix: `macos_compat.configure_macos_multiprocessing()` now sets `os.environ["PYTHONHOME"] = sys.prefix` (the *running* interpreter's prefix, which QGIS has remapped to a valid path like `Contents/Frameworks/`). Spawned workers inherit the env at spawn time and find the QGIS-bundled stdlib. Also added a `_can_spawn()` validation step in `find_macos_python_executable()` so we never return a binary that can't actually boot — and an `NOWIRES_PYTHON_EXE` env var override for users who want to point at a different Python (e.g. Homebrew).

  Measured speedup on the in-container `benchmarks/coverage_runtime.py`: small grid 6840 → **31038 px/s** (4.5×), medium grid 7318 → **44024 px/s** (6.0×), large grid 7416 → **48207 px/s** (6.5×). macOS users will see equivalent gains.

### Changed

- Added a Windows mirror of `configure_macos_multiprocessing` / `find_macos_python_executable` in a new `windows_compat.py`. `_can_spawn` is shared between the two via `from .macos_compat import _can_spawn`. The Windows helper looks for `pythonw.exe` first, then `python.exe`, in standalone and OSGeo4W-style bundle layouts (`<qgis>/pythonw.exe`, `<qgis>/../apps/Python3X/pythonw.exe`, `<qgis>/bin/pythonw.exe`, etc.), validates each candidate by actually launching it under a prepared env (`PYTHONHOME=sys.prefix`), and honours the `NOWIRES_PYTHON_EXE` env var as an explicit override. `pythonw.exe` is preferred so spawned workers don't pop a stray cmd window each (`python.exe` is a console-subsystem binary; `pythonw.exe` is the same interpreter without a console — pipe-based stdin/stdout/stderr still works, which is all `multiprocessing` uses).
- Replaced the v1.5.3-era `NOWIRES_WINDOWS_MP=1` opt-in env-var gate with the validating helper above. Windows multiprocessing is now self-adjusting: if `find_windows_python_executable()` returns a working interpreter, multiprocessing is on; otherwise the executor cleanly falls back to sequential with a clear log message.
- Removed cross-process cancel signaling from coverage multiprocessing entirely. `_itm_worker_batch` now takes a plain batch argument (no `(batch, event)` tuple) and the executor no longer creates an `Event` or `Manager`. Trade-off: cancel responsiveness drops from per-pixel to per-batch (~320 ms worst case for a 64-pixel batch at ~5 ms ITM/pixel).

### Added

- Added `tests/test_coverage_executor_spawn_safety.py` — 3 source-level contract tests asserting the executor does NOT use `multiprocessing.Event()` or `multiprocessing.Manager()`, and that `_itm_worker_batch` takes a plain batch argument. Catches regression to either of the broken patterns without needing a fork/spawn test harness.
- Added `tests/test_shared_dem_grid_name_length.py` — contract test that parses the literal name template in `shared_dem_grid.py` and asserts the total length (`/<prefix><N hex>`) stays under `PSHMNAMLEN = 31`. Future edits that lengthen the prefix or extend the hex suffix will fail loudly.

## [1.5.4] - 2026-05-16

### Fixed

- Fixed macOS `SIGABRT` crash when running Coverage Analysis with `ALLOW_THREADING` enabled. Previously `processAlgorithm` called `show_coverage_legend()` (which constructs and `.show()`s a `QFrame`) inline; with the v1.5.3 threading opt-in this ran on a `QThreadPool` worker, and Cocoa rejects `QWidget` creation off the main thread (`abort()` from `_initWithContentRect:`). The legend now stashes its `rx_sensitivity_dbm` on the algorithm instance during `processAlgorithm` and is shown from `postProcessAlgorithm`, which the QGIS Processing framework guarantees runs on the main thread. Linux/Xlib tolerated this pattern; macOS did not.

### Changed

- Extracted `_validate_dem_coverage` from `algorithm_coverage.py` to a new `coverage_dem_validate.py` helper module to keep `algorithm_coverage.py` within the 300-line cap after the new `postProcessAlgorithm` override.

### Added

- Added `tests/test_coverage_legend_deferred.py` — source-level contract tests asserting the legend show is deferred to `postProcessAlgorithm`. Catches regressions that would re-introduce the macOS crash without needing a real QGIS UI run.

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
