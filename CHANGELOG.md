# Changelog

SPDX-License-Identifier: GPL-3.0-or-later

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.6.6] - 2026-05-27

### Correctness

- P2P: add climate zone range validation matching coverage-path convention
- Clutter: surface WorldCover-unavailable fallback in report `clutter_model` field
- `geo_bounds`: enforce `MAX_AOI_EXTENT_DEGREES` with clamp-and-warn

### Robustness

- Antenna: cap pattern CSV reader at `MAX_PATTERN_ROWS=3600`, warn on truncation
- `TempDirManager`: broaden `__del__` exception catch to `(TypeError, AttributeError)`

### Changed

- `_bilinear.py`: extract shared `_compute_indices` from triplicated index logic
- `nan_utils`: return `np.ndarray` from `interpolate_nan_elevations` for consistency
- Expose `test_batch_philippines.py` to VC, add `@pytest.mark.slow`
- `cache_manager`: document `relatime`/atime limitation in `evict_cache_lru`
- Rename `_outputs_internal.py`/`_result_dispatch.py` dropping misleading underscore

### Added

- Concurrency safety tests for `SharedDEMGrid.release()`
- QGIS integration test for advanced clutter mode with WorldCover
- 10 new regression tests

## [1.6.5] - 2026-05-26

### Security

- Validate tile download redirect URL scheme in addition to netloc
- Strip query strings from tile URLs in user-facing feedback
- Fix CSV formula-injection bypass via leading regular space

### Correctness

- Fix SAALOS scalar/vector numerical asymmetry with mirrored clamps
- Warn when `K_FACTOR_PRESET` discards custom `K_FACTOR`
- Normalise JSON key `itm_path_loss_db` → `itm_loss_db` across P2P/coverage
- Omni preset: force `antenna_bw_override=360.0`, `antenna_az=None`
- Extract BEL to shared location, apply uniformly across both clutter modes
- Warn in simple-clutter mode when advanced-only params are set

### Robustness

- Add random jitter to tile download retry backoff
- Narrow SHM finalizer exception handling: `FileNotFoundError`/`OSError` only

### Changed

- Updated ROADMAP.md with revised test harness findings
- 10 new regression tests

## [1.6.4] - 2026-05-24

### Fixed

- Clamp `math.asin` in `bearing_destination` to `[-1.0, 1.0]`
- Hoist `urlsplit` import to module level in `tile_download_base`
- Replace hardcoded Earth radius with `EARTH_RADIUS_M` constant
- Remove dead store in `coverage_comparison.py`
- Remove unnecessary `Qt_rm` alias in `p2p/chart.py`
- Remove stale test comment

### Changed

- Add `GDAL_DRIVER_NAME` and `AOI_PADDING_FRACTION` to `constants.py` (12 sites)
- Add `SIGNAL_LEVELS` to `constants.py`, breaking `radio→radio_coverage` dep
- Move `grid_to_raster_array` to `raster_io`, breaking `raster_io→radio_coverage` dep
- Extract `aoi_padding_deg()` helper in `geo_bounds`
- Extract `csv_safe`/`sanitize_json` to `sanitizers.py`
- Replace ITM hardcoded defaults with `defaults.py` imports
- Split `clip_and_merge_tiles` into new `tile_merge.py`
- Stop `clutter/__init__.py` re-exporting private symbols

### Added

- 3 import-linter contracts: `radio`, `raster_io`, `tile_download_base` isolation
- Replace `type: ignore[arg-type]` with explicit `assert tmpdir is not None`
- Unit tests for `comparison/add_params.py`
- `__all__` to top-level `__init__.py`
- Move 6 orphaned scripts to `scripts/`
- `reviewers`/`labels` in `.github/dependabot.yml`

## [1.6.3] - 2026-05-24

### Fixed

- Clamp `math.asin` in `bearing_destination`
- Hoist `urlsplit` import to module level
- Replace Earth radius magic number with `EARTH_RADIUS_M`
- Remove dead store, dead alias, stale test comment

### Changed

- Add `GDAL_DRIVER_NAME`/`AOI_PADDING_FRACTION` to constants (12 sites)
- Add `SIGNAL_LEVELS` to constants, extract `aoi_padding_deg()` helper
- Move `grid_to_raster_array` to `raster_io`
- Extract `csv_safe`/`sanitize_json` to `sanitizers.py`
- Replace ITM hardcoded defaults with imports from `defaults.py`
- Split `clip_and_merge_tiles` into `tile_merge.py`
- Stop re-exporting private clutter symbols

### Added

- 3 import-linter contracts, `__all__` export, test for `comparison/add_params.py`
- Move orphaned scripts to `scripts/`

## [1.6.2] - 2026-05-23

> Breaking: rename `coverage/` subpackage to `radio_coverage/`.

### Fixed

- TOCTOU race in `dem_downloader`: `os.makedirs` → atomic `mkdtemp`+`rename`
- Configurable `max_bytes` download cap (250 MiB) for chunked transfers
- SHA-256 cache integrity via `.sha256` sidecar files
- Broaden CSV formula-injection guard (en-dash, minus, Unicode whitespace)
- `TempDirManager` leak in contour/coverage_comparison `__init__`
- OGR datasource leaks in contour pipeline/generation
- `SharedMemory.unlink()` in coverage pool finalizer for worker-crash paths
- Climate index range check (0–6) in `validate_itm_input_ranges`
- `ITMResult` failure sentinel: `mode=0` → `mode=-1`
- `threading.Lock` around coverage pool module globals
- Sample TX ground elevation from DEM in coverage comparison
- Validate per-feature antenna heights against ITM limits
- LRU cache eviction with 2 GiB cap
- `os.lstat` for symlink detection in SHM cleanup
- Guard against None GDAL driver in `raster_io`/contour smoothing
- Remove memory-doubling `np.copy` on south-up flip; 6 redundant copies in Fresnel
- Bool type guard in `antenna_preset_key`
- Warn on malformed CSV in antenna pattern reader
- Keep bilinear intermediates in float64
- NaN guard in SAALOS vectorized below-canopy path
- Singleton guard for P2P chart docks
- Fix `PANEL_A/B_CONSTANTS` dict keys for `install_constants`
- Worker atexit: `shm.close()` only; parent unlinks
- Prevent `FileNotFoundError` from inherited fork-atexit handlers
- Zero-dimension guards in `_bilinear.py`
- Capture/release `gdal.Translate` return in `package_gpkg`
- `safe_create_dir`: register temp dir on rename failure
- Contour: raise `QgsProcessingException` on `ENOSPC` instead of returning `{}`
- Add `exc_info=True` to contour proxy-auth exception handler
- Clamp scalar below-canopy exponent to `[-700, 700]`

### Added

- `tile_cache_integrity.py`, `fs_utils.py`, LRU eviction
- 49 regression tests across 11 files

### Changed

- CI: enforce coverage threshold, version downgrade guard, gate release on lint
- `pip-audit` full dependency tree, import-linter per AGENTS.md, SHA-pinned codeql
- `.gitignore`: add secrets/credentials patterns
- Centralize `DEM_NODATA`/`FSPL_CONSTANT`/`MHZ_TO_HZ`/`DIR_PERMISSIONS`/`K_FACTOR`
- Explicit `0.0` CCH override; wire `clear_pattern_cache` into preview file picker
- Centralize `create_synthetic_dem` in conftest
- Unify `dem_downloader`/`worldcover_downloader` on `safe_create_dir`
- **Breaking:** `coverage/` → `radio_coverage/`
- Replace `except Exception:pass` with `logger.debug(exc_info=True)`

### Security

- TOCTOU-safe `safe_create_dir` in p2p/compute, contour, comparison

## [1.6.1] - 2026-05-23

### Fixed

- Theta clamp in vectorized `building_entry_loss_vec` matching scalar path
- `interpolate_nan_array` all-NaN branch returns copy, not reference
- `_destroyed` guard in P2P chart to prevent stale closures
- Tighten TX position tolerance from 1e-3° to 1e-4°
- Restore `assert tmpdir is not None` in `resolve_output_paths`
- Remove unreachable `h_m <= 0.0` in P.2108 height gain
- Replace `f.close()` with `f.flush()` on download cancel
- Accept float timeout via `float()` in `_can_spawn`
- Use `DEFAULT_K_FACTOR` in Fresnel instead of hardcoded `4.0/3.0`
- `FlushCache()` on `gdal.Translate` result before release
- Replace NaN with empty string in CSV export
- Wrap `clutter_grid.close()` in try/except preserving original exception
- CSV formula-injection: `lstrip()` before trigger-character check
- `threading.Lock` around `_pending_releases` in `SharedDEMGrid`
- Skip ~20 MB array pre-allocation on empty coverage tasks
- `math.floor` cast for lat/lon in `tile_name_for`
- Mask `dist_grid_km` to NaN where `prx_grid` is NaN
- Debug logging for OOB bilinear samples
- ITM finite-loss guard: NaN/Inf returns None in batch
- Fix `tmpdir=None` assert crash in comparison reporting
- Relax TX tolerance in `validate_panels` from 1e-5° to 1e-3°
- Contour DEM failure: `QgsProcessingException` instead of `{}`
- Comparison: `QgsProcessingException` instead of bare `ValueError`
- Matplotlib figure leak: `fig.clear()`+`plt.close(fig)` in `_on_destroy`
- Headless QGIS guard in `show_profile_chart`
- `FlushCache()` on hillshade dataset before release
- P2P chart failure: `feedback.pushWarning` alongside `logger.warning`
- P.2109-2 theta clamp to 0–90°
- P.2108-1 near-zero height floor at `_MIN_HEIGHT_M=0.1 m`
- Validate panel grid sizes early in coverage comparison
- Add climate zone to P2P feedback and batch/comparison output
- SAALOS scalar/vector formula consistency: `exp(1/cch - htx)`

### Added

- 7 Fresnel edge-case tests, 15 clutter edge-case tests
- 5 comparison reporting tests, 15 coverage algorithm tests
- 10 algorithm integration tests, 7 batch infrastructure tests
- 8 coverage infrastructure tests, 6 clutter grid tests
- 10 tile download tests, 15 p2p chart extended tests
- 13 dem downloader edge-case tests, 7 cache manager tests
- Coverage from 59% to 66% (+143 tests, +420 covered statements)
- `test_batch_philippines.py`, contour pipeline integration, climate-variation test
- Hypothesis property-based tests, MP execution smoke test

### Changed

- Convert fragile `inspect.getsource()` test to behavioral
- Revert early-validate test to source check
- Strengthen `dist_nan_mask` assertion

## [1.6.0] - 2026-05-19

### Refactor

- Reorganize into 8 subpackages (algorithm, batch, comparison, contour, coverage,
  clutter, p2p, report). 60 modules relocated. All imports → `NoWires.X`.
- Import-linter contract: ITM must not depend on qgis/PyQt.
- **NOTE:** Restart QGIS after upgrading; Plugin Reloader retains stale references.

## [1.5.12] - 2026-05-18

### Changed

- Extract `build_link_clutter_context()` factory, dedup 14-field construction
- Replace inline Fresnel/LOS in batch with `fresnel_profile_analysis` call
- Switch comparison panel to `build_initial_clutter_context` factory
- Extract `ComparisonPanelParams` dataclass + `collect_panel_params` factory
- Consolidate `tx_h_eff` resolution in batch link computation

### Added

- 13 unit tests for `collect_panel_params`, 4 for `build_link_clutter_context`
- 32 drift-guard snapshot tests for clutter math modules

## [1.5.10] - 2026-05-17

### Fixed

- Windows `geteuid` AttributeError via `hasattr` guard
- P2P chart checkbox toggles needing `fig.canvas.draw_idle()` to repaint
- `NameError` when tx/rx markers undefined in visibility toggle
- `AttributeError` on None antenna config in gain adjustment
- Clutter grid leak on early exception in P2P
- Fresnel longitude wrap across antimeridian
- Dead `_ChartCanvas.closeEvent` — use dock signal instead
- `setFloating` called before `addDockWidget`
- Obstruction sort by deficit, not terrain height
- Return `fresnel_lines_path` from output writer
- Validate `f_mhz`/`k_factor` in Fresnel calculations
- Fix `build_obstruction_data` docstring

### Added

- Regression tests for chart visibility, antenna None guard, clutter grid leak,
  lon wrap, obstruction sort, output layer path, Fresnel input validation

### Changed

- SHA-pin codeql actions; add `needs:[lint]` to integration; remove unused marker
- Add `pip check` to integration; extract QGIS mocks; explicit zip manifest

## [1.5.9] - 2026-05-17

### Fixed

- Tile download: don't purge structurally-valid cache on `ComputeStatistics` failure
- Remove overall wall-clock deadlines that false-tripped on large areas

### Added

- Regression tests for cache stats tolerance and no-overall-deadline

## [1.5.8] - 2026-05-17

### Changed

- Decompose `coverage_pool`/`p2p_compute`/`contour_smoothing` (300-line compliance)
- Replace 12 magic numbers with constants (`METERS_PER_DEGREE_LAT`, `DEFAULT_FREQ_MHZ`, etc.)
- Add named smoothing/delta/clutter constants; collapse `_atexit_cleanup` alias
- Convert 7 silent `except:pass` to `logger.debug`; narrow to `OSError`
- Drop duplicate `ProcessPoolExecutor` re-export; add `WGS84_CRS` singleton
- Move `FRESNEL_60PCT_FACTOR` to constants; add `EMPTY_MARGIN_DB`, `BYTES_PER_MEBIBYTE`
- `from __future__ import annotations` across 7 p2108 modules
- Replace last `CONTOUR_LAYER_KEY` literal; reconcile MP-fallback message
- Replace `type: ignore` with `assert tmpdir is not None`
- Break `clutter↔clutter_advanced` import cycle; extract `_bilinear.py`
- Promote underscore-private clutter symbols; add `ClutterModel`/`BuildingType` literals
- `WorkerError` sentinel replacing length-tag dispatch

### Added

- Tests for p2108 category derivation and WorkerError sentinel

## [1.5.7] - 2026-05-17

### Fixed

- Haversine NaN: `np.clip(a, 0.0, 1.0)` before `arcsin`
- `assert`→`RuntimeError` in ElevationGrid (enforced under `-O`)
- Batch: don't close user-supplied clutter grid (`owns_clutter_grid` flag)
- Coverage pool: gate atexit re-registration; accumulate partial MP counters
- GDAL leak in contour clip verification; antenna-preview dialog lifecycle
- Latitude clamp + `METERS_PER_DEGREE_LAT` in `coverage_bounds`
- Per-param defaults for Time/Location/Situation percentage
- `FlushCache` before hillshade release; `TempDirManager` for contour fallback
- Zero-division guards in `ElevationGrid` and `summarize_coverage_grid`
- Weak-reference atexit registry for `SharedDEMGrid`

### Added

- 14 regression tests per TDD convention

## [1.5.6] - 2026-05-17

### Fixed

- Windows `PicklingError`: resolve `_init_cov_pool`/`_itm_worker_batch` lazily inside
  `execute_coverage_tasks` to avoid stale references after QGIS plugin reload

### Changed

- MP-fallback diagnostic: route exception details through QGIS feedback channel

## [1.5.5] - 2026-05-16

### Fixed

- macOS MP: truncate SHM name hex suffix to 16 chars (PSHMNAMLEN=31)
- macOS MP: remove cross-process cancel `Event()` incompatible with `spawn`
- macOS MP: set `PYTHONHOME=sys.prefix` so spawned workers find QGIS-bundled stdlib
- Measured 4–6× pixel/sec speedup on macOS coverage

### Changed

- Windows MP: auto-detect `pythonw.exe`/`python.exe` with validation fallback
- Remove `NOWIRES_WINDOWS_MP` opt-in; cancel responsiveness per-batch (~320 ms)

### Added

- Tests for spawn safety and SHM name length contract

## [1.5.4] - 2026-05-16

### Fixed

- macOS SIGABRT: defer coverage legend `QWidget` creation to `postProcessAlgorithm`

### Changed

- Extract `_validate_dem_coverage` to keep `algorithm_coverage.py` ≤300 lines

### Added

- Source-level contract test for deferred legend show

## [1.5.3] - 2026-05-16

### Added

- PDF report output via Qt `QTextDocument`+`QPrinter`
- Antenna pattern preview dialog (polar plot via `QPainter`)
- `LinkBudgetBundle`/`extract_link_budget_params` dedup in `shared_params`
- `build_initial_clutter_context` factory; `NOWIRES_WINDOWS_MP` env var
- Golden-file report export tests; PDF writer fallback test

### Changed

- Plugin GUI registration via single table (–50 lines)
- Contour smoothing: explicit `_parse_xml` instead of global monkey-patch
- Vectorize elevation fallback (192× fewer calls); double progress buckets
- HTTP failures surface status+timing through feedback
- Pool init resets stale state instead of raising; 9 type:ignore reasons

### Added (thread/UX)

- `ALLOW_THREADING` on Coverage/Batch/Comparison for responsive UI
- Per-tile 180s wall-clock budget; cache size/confirmation helpers
- `ClutterParamBundle` extraction dedup

## [1.5.2] - 2026-05-15

### Added

- `clear_pattern_cache()` API; GDAL `UseExceptions()` at startup
- Batch multipart geometry handling; contour CRS fallback
- NaN-aware elevation interpolation in batch P2P
- 8 new test suites (integration, hypothesis, I/O)
- CI: pytest, pip-audit, ruff, version/changelog enforcement, concurrency groups

### Fixed

- `METERS_PER_FOOT` correction for feet-to-meter conversion
- Mypy annotations across 20+ modules; dead code removal
- CI: missing `mypy.ini`, `continue-on-error` removal, QGIS 3.34 dropped

## [1.5.1] - 2026-05-12

### Added

- "Clear DEM Cache" menu + `cache_manager.py` (size-aware cleanup)

### Fixed

- User clutter grid ownership; dedup numpy scans in report display
- Qt6 chart crash (Windows); comparison advanced clutter controls
- Antimeridian P2P geometry; `_owns_clutter` UnboundLocalError
- Coverage TX marker and P2P output layer persistence
- 14 code review fixes: resource leaks, metric consistency, API correctness

### Changed

- `.gitignore`: added `.coverage`; persistent output paths under user temp dir

## [1.5.0] - 2026-05-07

### Added

- Advanced clutter correction mode (SAALOS, P.2108, P.2109)
- 5 clutter sub-modules; 62 clutter tests
- `CLUTTER_PERCENTILE`, `STREET_WIDTH_M`, `BEL_ENABLED/TYPE/ANGLE` params

### Changed

- P.2108 replaced simplified loss model; dispatch per-category per §6 compliance
- P2P/coverage/batch/comparison pipelines adopt advanced clutter context

### Fixed

- `ModuleNotFoundError` for `clutter_constants`; coverage heatmap near-transmitter
- P2P clutter grid handle leak; TOCTOU temp dir races
- macOS MP compatibility; P.2108 frequency factor unification
- Coverage pool fallback; duplicate clutter compute; elevation pixel offset

## [1.4.0] - 2026-05-03

### Added

- Batch P2P, Coverage Comparison, P2P chart+reports, coverage reports, reliability
- Coverage opacity slider, 3D scene tracking, P2P rule-based symbology
- Shared modules: params, DEM grid, GeoTIFF writer, NaN utils, temp manager

### Changed

- Architecture: monoliths → focused helper modules (coverage, contour, batch, p2p)
- Constants → `constants.py`/`defaults.py`; base algorithm → `base_algorithm.py`

### Fixed

- VRT smoothing no-op; comparison delta `COVERAGE_NODATA` normalization
- `postProcessAlgorithm` for project state; dead `_cleanup_cov_pool` removed
- `unload()` AttributeError; URL redirect validation; FSPL constant `32.44→32.45`
- RX cable loss in power calc; NaN worker warning; ITM failure → NaN sentinel
- CSV/JSON injection; per-param defaults for pct values; `_feat_attr` dispatch
- `super().unload()`; NaN percentages on zero valid_count; layer validity warnings
- UnboundLocalError on `clutter_grid`; `gdal.Warp` NoData remap; COVERAGE_NODATA norm
- `f.flush()+os.fsync` before tile rename; temp dir permission check

## [1.3.0]

### Added

- Antenna presets + pattern CSV support; simple clutter correction with WorldCover
- `worldcover_downloader.py`; `clutter_source_label()` helper
- Coverage report: clutter loss components

### Changed

- Clutter source labels via helper; coverage TX clutter as representative

### Fixed

- ITM: `smooth_earth_diffraction` log guard (NC1); per-task exception handling (NC2)
- MP cancel event (NI1); worker SHM close on pool shutdown (NI2)
- `COVERAGE_NODATA` constant (NI3); dead contour TYPE field (NI4)
- `_feat_attr` type coercion logging (NI5); `Retry-After` header honouring (NI6)
- Socket timeout constants (NI7); 38 ITM reference-vector tests (NM9)
- Qt6 `QAction` import; P2P clutter grid bounding box fix

## [1.2.0]

- Remove `gdal_calc.py`; fix critical `report_payloads` import
- Vectorize coverage distance; replace VRT string manipulation with XML parsing
- Namedtuples for coverage tasks; remove global GDAL config side effects
- NaN for nodata in ElevationGrid; remove legacy `sys.path` manipulation
- Fix imports/copyright headers; extract magic number constants
- Split coverage helpers; add synthetic benchmark; live opacity action
- 3D scene support; CSV/JSON/HTML reports; TX/RX markers; reliability output
- Fix raster cell-center alignment; north-up DEM sampling; Windows access violation
- Fix double-loading conflict; DEM layer ordering; missing `ANTENNA_AZ` constant

## [1.1.0]

- Replace area coverage + radius sweep with unified Coverage Analysis
- Add raster-derived coverage range statistics
- Improve coverage raster styling and controls
