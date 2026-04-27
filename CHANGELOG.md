# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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

- Fix Qt 6 `QAction` import location and keep source checks for direct Qt 6 enum usage.
- Fix P2P clutter grid download bounding box: WorldCover tiles are now fetched after the padded TX–RX extent is known, preventing zero-area downloads when the TX and RX are close together.

## [1.2.0]

- Remove `gdal_calc.py` (dead code with `eval()` usage and deprecated `optparse`).
- Remove `algorithm_coverage_radius.py` (dead code — was never registered in the provider).
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
