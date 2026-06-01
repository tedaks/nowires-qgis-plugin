# Changelog

SPDX-License-Identifier: MIT

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING:** Relicensed the plugin's own source from GPL-3.0-or-later to the **MIT License**. Only 3.0.0 and later are MIT; pre-3.0.0 releases remain GPL. The `itm/` files stay US-Government public domain (NTIA disclaimer).
- **BREAKING:** Removed the Contour Lines feature — the `contour_lines` algorithm, the `contour/` package, and the hillshade overlay — whose code derived from the GPL ContourLines plugin. The provider now registers 4 algorithms. Users needing contour lines should install the standalone [ContourLines](https://plugins.qgis.org/plugins/ContourLines/) plugin.
- Clean-room reimplemented the shared DEM download core (`dem_downloader.py`, `tile_download_base.py`) as original work from public Copernicus GLO-30 specifications, removing the last GPL-derived code (see CLEANROOM.md). Public APIs are unchanged.

### Correctness

- Fix `test_decouple_n0_registered_and_not_advanced` failing on Python 3.13 — replace `MagicMock.called` (removed in 3.13) with dual-path check that also works against real QGIS bindings.

## [2.0.0] - 2026-05-31

### Correctness

- Import `logging` and define `logger` in `algorithm/p2p.py` to fix `NameError` on chart display failure.
- Move `import numpy as np` to module level in `clutter/p833.py` and wrap return with `float()` for type-safety.
- Make `_FakeQgsApplication` mock accept constructor arguments so QGIS integration tests can run without a real QGIS runtime.

### Cleanups

- Remove unused imports (`pytest`, `math`, `sys`) and a duplicate `sys` import from four test files.
- Decompose `download_tile_with_retry` into four staged helpers: `_serve_from_cache`, `_download_to_tmp`, `_validate_downloaded_tile`, `_classify_http_error` (`tile_download_base.py`).
- Add `.mcp.json` and `provider_config.json` to `.gitignore`.
- Add pip upgrade step to `audit` CI job to suppress pip-self CVE noise.
- Add focused unit tests for `batch/params.py` (`tests/test_batch_params.py`).
- Document package-name requirement (`NoWires`) in `AGENTS.md` and `USERS-GUIDE.md`.
- Add reproducible local dev-environment bootstrap to `CONTRIBUTING.md`.

### Breaking Changes

- **`ClutterLossContext`** — removes three fields that were only consumed by
  saalos: `polarization`, `rx_ground_elevation_m`, `tx_ground_elevation_m`.
  Any code constructing `ClutterLossContext` directly or calling
  `build_initial_clutter_context` / `build_link_clutter_context` with those
  keyword arguments must be updated.
- **`clutter/saalos.py` deleted** — `clutter_loss_saalos`,
  `clutter_loss_saalos_vec`, and `_saalos_pol` are no longer importable.
  Replace with `clutter_loss_p833` / `clutter_loss_p833_vec` from
  `clutter/p833.py`.
- **`MAX_CLUTTER_LOSS` removed** from `clutter/constants.py` — the constant no
  longer exists; the P.833-9 Am formula has no cap.
- **Vegetation clutter values change** — saalos returned a fixed 22.0 dB at any
  frequency. P.833-9 Am is frequency-dependent: lower below ~850 MHz, higher
  above 1 GHz. Results for existing coverage analyses will differ.
- **K-factor preset now sets surface refractivity N0** — selecting a
  non-default `K_FACTOR_PRESET` in P2P/Batch overrides N0 (0.67→250, 1.00→280,
  1.33→301, 2.00→350, 4.00→400 N-units) and therefore changes the ITM
  propagation prediction, not just the Fresnel/LOS display. The standard 1.33
  default still maps to N0=301, so default-preset runs are unchanged. Enable
  the new "Decouple N0 from k-factor preset" checkbox or choose the Custom
  preset to keep N0 independent (the pre-2.0.0 behaviour).

### Security / Licence

- Replace `clutter/saalos.py` and `clutter/_saalos_vec.py` (derived from
  ITWOM 3.0, copyright © 2011 Sid Shumate / Givens & Bell, Inc., proprietary)
  with a clean implementation of ITU-R P.833-9 §2.1 Am. No proprietary upstream
  code remains in the repository. `NOTICE.md §7` updated accordingly.

### Added

- `clutter/p833.py` — `clutter_loss_p833(cch_m, h_rx_m, f_mhz)` (scalar) and
  `clutter_loss_p833_vec` (vectorised NumPy). Implements Am = 1.37 × f^0.42
  from ITU-R P.833-9 §2.1 (St. Petersburg fit, 105.9–2117.5 MHz). Returns 0.0
  when the antenna is at or above the canopy height.
- `tests/test_clutter_p833.py` — 10 tests covering boundary conditions, Am
  reference values, frequency monotonicity, no-cap assertion, and scalar/vec
  agreement.
- `DECOUPLE_N0` processing parameter on the P2P and Batch algorithms — an
  opt-in checkbox that restores the pre-2.0.0 behaviour where the k-factor
  preset affects only the Fresnel/LOS display and N0 stays user-controlled.
- `k_factor_presets.py` — houses `K_FACTOR_PRESETS`, the new
  `K_FACTOR_PRESET_N0` coupling table, and `resolve_k_factor` / `resolve_n0`
  (re-exported from `radio` for compatibility).
- `tests/test_k_factor_n0_coupling.py`,
  `tests/test_k_factor_preset_backward_compat.py` — lock the coupled N0 values,
  the Custom-preset and decouple escape hatches, and the ITM loss change.

### Removed

- `clutter/saalos.py`, `clutter/_saalos_vec.py` — replaced by `clutter/p833.py`.
- `tests/test_clutter_saalos.py`, `tests/test_saalos_nan_guard.py`,
  `tests/test_saalos_above_canopy_nan.py` — superseded by
  `tests/test_clutter_p833.py`.
- `tests/test_clutter_constants.py` — tested `MAX_CLUTTER_LOSS == 22.0`;
  constant deleted.
- `_build_rx_ground_grid` and `_get_tx_ground_elevation` from
  `radio_coverage/engine.py` — eliminated an O(grid²) DEM sample pass that ran
  before every advanced-mode coverage analysis.
- `both_saalos` dead-code branch in `clutter/advanced.py:compute_terminal_clutter_losses`.
- Saalos special-cases in `compute_path_clutter_loss` (both-saalos max and
  mixed-saalos logic). P.833 terminal losses are now summed like any other
  independent clutter contribution.

### Changed

- `clutter/categories.py` — `"vegetation"` model key changed from `"saalos"` to
  `"p833"`.
- `ClutterLossContext` — fields `polarization`, `rx_ground_elevation_m`,
  `tx_ground_elevation_m` removed (see Breaking Changes).
- `compute_path_clutter_loss` — saalos-specific path logic removed; vegetation
  (p833) losses are now summed across both terminals.
- K-factor preset label changed from "Fresnel Earth-radius factor (display
  only)" to "Earth-radius factor (k) — sets N0"; the N0 field is now
  documented as preset-driven unless decoupled.
- `radio_coverage/tasks.py` — LUT key simplified to distance bucket only
  (ground elevation bucket removed).
- All documentation updated: `Technical_Documentation.md`, `USERS-GUIDE.md`,
  `README.md`, `NOTICE.md §7`.

## [1.7.1] - 2026-05-30

### Correctness

- ITM: K-factor parameter now correctly flows into the smooth-earth diffraction
  calculation. Previously `K_FACTOR_PRESET` and `K_FACTOR` were resolved to a
  float but that value was never forwarded to `itm_p2p_loss` → `predict_p2p` →
  `longley_rice` → `smooth_earth_diffraction`; the engine silently used the
  hard-coded constant `4/3` for every run. The parameter now threads through all
  five layers so sub-refractive (k=0.67) and super-refractive (k=2.0, 4.0)
  atmospheres produce distinct diffraction losses on NLOS paths, as intended.
  Fresnel-zone visualization and report display were already correct.
- Batch: `itm_p2p_loss` call in `_compute_single_link` was missing the
  `k_factor` parameter; the batch algorithm silently used the default 4/3 for
  every link regardless of the user's K-factor preset selection
- Post-processing: `base_algorithm.py` and `contour.py` `postProcessAlgorithm`
  now use `context.project()` instead of `QgsProject.instance()` for layer-tree
  reorder and `writeEntry`, so layers and metadata land on the correct project
  in Model Designer, batch processing, and headless contexts
- `queue_layer_for_loading` now resolves the project from `context.project()`
  instead of always using the global singleton, fixing layer placement in
  non-interactive execution contexts

### Robustness

- Validation: `validate_itm_input_ranges` now also validates time/location/situation
  percentages (0.01–99.99%), k-factor (> 0.01), and earth permittivity epsilon
  (≥ 1.0), failing fast before the potentially long DEM download
- Coverage algorithm now calls `validate_itm_input_ranges` before `ensure_dem_for_area`,
  so invalid inputs error in ~1 s instead of after a 30 s download
- P2P and Contour algorithms now opt into threading (`ALLOW_THREADING = True`),
  restoring a responsive, cancellable UI during DEM downloads; chart creation is
  deferred to `postProcessAlgorithm` which runs on the context's affinity thread
- Pre-run AOI summary: `ensure_dem_for_area` now pushes a one-line feedback
  message with AOI dimensions, tile count, estimated download size, and pixel count
  before the blocking download (e.g. "AOI 0.8°×0.8°, 4 tiles ~120 MB, 5.2 M pixels")

### Changed

- `highlight_nowires_layers` and `open_nowires_3d_view` accept an optional
  `project` parameter for testability; default remains `QgsProject.instance()`

## [1.7.0] - 2026-05-28

### Correctness

- Coverage: handle antimeridian wrapping in cell-center generation to produce tasks near ±180°
- ITM: use tolerance-based check for kHat near-zero fallback instead of exact float equality
- BEL: compute Building Entry Loss in simple-clutter mode for P2P and Batch algorithms
- BEL: decouple BEL computation from `clutter_enabled` flag so BEL applies independently
- Proxy: validate realm URL hostname and port before building opener URL
- K-factor: relabel parameter to clarify it affects only Fresnel/LOS display, not ITM propagation
- Coverage/Comparison: warn when ANTENNA_PRESET=0 (Omni) silently discards user-supplied beamwidth and downtilt values
- Coverage/P2P: write temporary output layers under the saved project directory so layers survive reboot and cross-machine transfer
- Project paths: guard `_project_or_temp_dir` against `None` project context (standalone test contexts, unsaved projects)

### Changed

- Coverage: extract algorithm helpers into `algorithm/_coverage_helpers.py` to stay under the 300-line source cap and prepare for Phase 3 dataclass migration
- Contour: remove dead `contour_shp_path is None` check (the path is built unconditionally)
- P2P algorithm: remove dead `try/finally` around `run_p2p_analysis` (the finally body was just `pass`)

### Robustness

- `__del__`: broaden exception guards to catch `AttributeError` alongside `TypeError`
- `__del__`: move attribute check inside try block in `TempDirManager`
- `tile_merge`: wrap `ThreadPoolExecutor` in `with` block to prevent thread leak
- P2P: clamp AOI latitude bounds to [-90, 90] for polar links
- SAALOS: guard above-canopy branch against NaN propagation
- Elevation: produce contiguous array after south-up DEM flip for bilinear hot path

### Added

- 3D view: remember the last Coverage, P2P, and Contour output layers so "Open 3D View" reuses them without re-running

## [1.6.6] - 2026-05-27

### Correctness

- P2P: add climate zone range validation matching coverage-path convention
- Clutter: surface WorldCover-unavailable fallback in report `clutter_model` field
- `geo_bounds`: enforce `MAX_AOI_EXTENT_DEGREES` with clamp-and-warn
- Coverage: extend report input echo to include all engine-consumed parameters
- Engine: update simple-mode clutter warnings — BEL and TX override now mode-independent

### Robustness

- Antenna: cap pattern CSV reader at 3600 rows, warn on truncation
- GPKG writers: use 25D geometry types to suppress Z-type warnings
- `tile_merge`: add 30s `ComputeStatistics` timeout to prevent UI hang

### Changed

- `_bilinear.py`: extract shared `_compute_indices` from triplicated index logic
- `radio_coverage/params.py`: add omni preset guard for BW/AZ matching comparison path
- 16 new regression tests

## [1.6.5] - 2026-05-26

### Security

- Validate tile download redirect URL scheme; strip query strings from feedback

### Correctness

- SAALOS scalar/vector numerical symmetry; BEL shared across both clutter modes
- Normalise report JSON keys; omni preset overrides custom antenna params
- Warn when `K_FACTOR_PRESET` discards custom `K_FACTOR`

## [1.6.4] - 2026-05-24

### Changed

- Centralize 12 magic constants; extract reusable helpers (`aoi_padding_deg`, `sanitizers`)
- Add 3 import-linter architectural contracts; `__all__` public API surface
- Split `clip_and_merge_tiles` into `tile_merge.py`

## [1.6.3] - 2026-05-24

- Cascade of v1.6.4 changes after rebase — same content, different date.

## [1.6.2] - 2026-05-23

> Breaking: rename `coverage/` subpackage to `radio_coverage/`.

### Security

- SHA-256 cache integrity; TOCTOU-safe `safe_create_dir`; broaden CSV formula-injection guard

### Fixed

- Resource leaks: `TempDirManager`, OGR datasources, `SharedMemory.unlink()`, GDAL handles
- Climate range validation in ITM; `ITMResult` failure sentinel unambiguity
- LRU cache eviction (2 GiB cap); NaN/singleton/zero-dimension guards
- Configurable download cap (250 MiB); worker atexit cleanup

## [1.6.1] - 2026-05-23

### Fixed

- P.2108/P.2109 model corrections: theta clamp, near-zero height floor, BEL vector symmetry
- Chart/dialog lifecycle: Qt6 crash, matplotlib leak, headless guard, singleton docks
- ITM NaN/Inf guard in batch; Fresnel default-k-factor constant
- Coverage: empty-task memory skip, NaN-mask distance grid

### Added

- 143 tests (+7% coverage); hypothesis property tests; MP smoke test

## [1.6.0] - 2026-05-19

> **Breaking:** 60-module reorganisation into 8 subpackages. Restart QGIS after upgrade.

## [1.5.12] - 2026-05-18

- Extract shared clutter context factories; dedup batch Fresnel/LOS with call to standard helper
- 49 unit tests for clutter math and parameter collection

## [1.5.10] - 2026-05-17

- Fix P2P chart visibility, obstruction sort, Fresnel antimeridian, clutter grid leak
- Windows/macOS/headless guards for platform portability

## [1.5.9] - 2026-05-17

- Don't purge valid cache on `ComputeStatistics` failure; remove overly-aggressive deadlines

## [1.5.8] - 2026-05-17

- 300-line file decomposition; centralize 12+ magic numbers; break import cycle
- 7 silent `except:pass` converted to `logger.debug`; `WorkerError` sentinel pattern

## [1.5.7] - 2026-05-17

- Haversine stability, ElevationGrid safety, resource lifecycle (GDAL, atexit, dialogs)
- Per-parameter defaults for time/location/situation percentages

## [1.5.6] - 2026-05-17

- Windows multiprocessing `PicklingError` fix — lazy function resolution on plugin reload

## [1.5.5] - 2026-05-16

### Fixed

- macOS multiprocessing: SHM name truncation, spawn-mode cross-process cancel, QGIS stdlib path
- 4–6× pixel/sec speedup on macOS coverage

### Changed

- Windows MP auto-detect replaces `NOWIRES_WINDOWS_MP` opt-in

## [1.5.4] - 2026-05-16

- macOS SIGABRT: defer coverage legend to main thread

## [1.5.3] - 2026-05-16

### Added

- PDF report output, antenna pattern preview dialog, golden-file export tests
- `ALLOW_THREADING` on Coverage/Batch/Comparison for responsive UI
- Per-tile 180s download budget; cache size confirmation helpers

## [1.5.2] - 2026-05-15

- `clear_pattern_cache()` API; GDAL `UseExceptions()` at startup
- CI pipeline: pytest, pip-audit, ruff, version/changelog enforcement
- Fix feet-to-meter constant; mypy annotations across 20+ modules

## [1.5.1] - 2026-05-12

- "Clear DEM Cache" menu; user clutter grid ownership fix
- Qt6 chart crash (Windows); antimeridian P2P geometry; persistent output layers

## [1.5.0] - 2026-05-07

### Added

- Advanced clutter correction (SAALOS, ITU-R P.2108 §3.1/§3.2, P.2109 BEL)
- `CLUTTER_PERCENTILE`, `STREET_WIDTH_M`, `BEL_ENABLED/TYPE/ANGLE` parameters

### Changed

- P.2108 replaced simplified model; per-category dispatch per §6 compliance

## [1.4.0] - 2026-05-03

### Added

- Batch P2P, Coverage Comparison, P2P profile chart, coverage/contour reports
- Coverage opacity slider, 3D scene support, reliability outputs
- Architecture: monoliths → focused helper modules

### Fixed

- VRT smoothing no-op; ITM failure NaN sentinel; CSV/JSON injection
- Windows crash from unsafe project state mutation; double-loading conflict
- FSPL constant correction; RX cable loss in power calculation

## [1.3.0]

### Added

- Antenna presets + custom pattern CSV support; simple clutter correction with WorldCover

### Fixed

- ITM smooth-earth diffraction guard; per-task exception handling (MP robustness)
- `Retry-After` header honouring; socket timeout constants; Qt6 compatibility

## [1.2.0]

- Remove dead `gdal_calc.py`; vectorize coverage distance; namedtuple task bundles
- Fix raster alignment, north-up DEM, Windows crash, double-loading conflict
- CSV/JSON/HTML reports; TX/RX markers; reliability output; 3D scene tracking

## [1.1.0]

- Unified Coverage Analysis replacing area coverage + radius sweep
- Raster-derived coverage range statistics; improved heatmap styling
