# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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

## [1.1.0]

- Replace separate area coverage and radius sweep workflows with unified `Coverage Analysis`.
- Add raster-derived coverage range statistics.
- Improve coverage raster styling and controls.
- Add regression coverage for Processing contracts and coverage behavior.
