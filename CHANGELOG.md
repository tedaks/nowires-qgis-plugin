# Changelog

SPDX-License-Identifier: GPL-3.0-or-later

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.0] - 2026-05-28

### Correctness

- Coverage: handle antimeridian wrapping in cell-center generation to produce tasks near ±180°
- ITM: use tolerance-based check for kHat near-zero fallback instead of exact float equality
- BEL: compute Building Entry Loss in simple-clutter mode for P2P and Batch algorithms
- BEL: decouple BEL computation from `clutter_enabled` flag so BEL applies independently
- Proxy: validate realm URL hostname and port before building opener URL
- K-factor: relabel parameter to clarify it affects only Fresnel/LOS display, not ITM propagation

### Robustness

- `__del__`: broaden exception guards to catch `AttributeError` alongside `TypeError`
- `__del__`: move attribute check inside try block in `TempDirManager`
- `tile_merge`: wrap `ThreadPoolExecutor` in `with` block to prevent thread leak
- P2P: clamp AOI latitude bounds to [-90, 90] for polar links
- SAALOS: guard above-canopy branch against NaN propagation
- Elevation: produce contiguous array after south-up DEM flip for bilinear hot path

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
