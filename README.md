# NoWires — QGIS Plugin

Radio propagation analysis and terrain tools powered by NTIA's Irregular Terrain Model (ITM) with Copernicus GLO-30 DEM.

## Status

This repository contains the QGIS 4 plugin source for **NoWires** version 1.5.5.

Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
SPDX-License-Identifier: GPL-3.0-or-later

## Features

### Radio Propagation
- **Point-to-Point Analysis**: Place TX and RX points on the map. Computes ITM path loss, terrain profile with Fresnel zone analysis, generates CSV/JSON/HTML reports, and creates vector layers for the link path, Fresnel geometry, and TX/RX markers. Includes an interactive profile chart with hover callouts and export.
- **Batch P2P Analysis**: One-to-many and many-to-one batch link computation. Ranks results by link margin and outputs a combined results layer.
- **Coverage Analysis**: Place a transmitter, set a max analysis distance and grid resolution, then generate a heatmap raster showing received signal strength (dBm) plus range statistics derived from cells above sensitivity, with optional CSV/JSON/HTML report export. Coverage cells are sampled and georeferenced at cell centers so the heatmap lines up with the terrain and requested map extent.
- **Coverage Comparison**: Side-by-side coverage comparison producing a delta raster (Panel A – Panel B in dB) with dual-panel statistics and optional report export.
- **Antenna Presets And Pattern Files**: Antenna presets for omni, sector, and dish-style pattern planning, with optional horizontal/vertical pattern CSV files.
- **Clutter / Land-Cover Correction**: Three clutter modes are available:
  - **Off** — no terminal clutter correction.
  - **Simple clutter correction** — flat per-category losses (legacy behaviour, unchanged).
  - **Advanced clutter correction** — ITU-R P.2108-1 §3.1 height-gain terminal correction for rural categories (0.03–3 GHz); P.2108-1 §3.2 statistical clutter loss for suburban/urban (0.5–67 GHz); saalos for vegetation. Suburban/urban categories use both §3.1 and §3.2 in the overlap band (0.5–3 GHz) and take the maximum. When the antenna is at or above the canopy height, the model gates the loss to zero for that terminal.
  - **Building entry loss (BEL)** — ITU-R P.2109-2 indoor penetration loss for the RX terminal, with traditional/thermally-efficient building types and elevation angle support. Enabled under advanced clutter settings.
  Reports include per-terminal clutter loss (`clutter_tx_db`, `clutter_rx_db`), canopy heights (`tx_cch_m`, `rx_cch_m`), `total_path_loss_db` breakdown, BEL (`bel_rx_db`), and combined total (`total_with_bel_db`). WorldCover 2020 tiles are auto-downloaded from the ESA AWS open data bucket when clutter is enabled and no raster is supplied; users can also provide a local raster.
- **Reliability Outputs**: P2P and coverage reports now include fade-margin classes plus formal-or-fallback availability guidance.
- **Coverage Opacity Control**: Adjust the most recent coverage raster opacity from a live plugin dialog after the analysis finishes.

### Terrain Analysis
- **Contour Lines**: Generate contour lines with rule-based symbology (index contours with labels) from Copernicus GLO-30 DEM. Adjustable interval (1–5000 m or ft), four smoothing levels, and custom colour.
- **Hillshade Overlay**: Optional hillshade elevation layer rendered from the raw DEM with Dodge blending.
- **3D Scene Support**: Coverage and contour workflows track the latest DEM and derived layers for opening a QGIS 3D view. On Windows, use QGIS's native `View -> 3D Map Views -> New 3D Map View` workflow because plugin-launched 3D canvases are disabled there for stability.

### DEM Data
- All DEM data is automatically downloaded from the **Copernicus GLO-30** dataset hosted on AWS Open Data.
- No API key or account required.
- Tiles are cached locally for reuse in subsequent runs.

## Requirements

### Runtime (end users)

- QGIS 4.0 or later
- Qt 6 / PyQt 6 as bundled with QGIS 4
- Internet connection (for DEM tile downloads)
- GDAL (bundled with QGIS)
- numpy (bundled with QGIS)

NoWires does not maintain a Qt 5 compatibility layer. Source code uses QGIS 4 / Qt 6 APIs directly.

No additional Python packages need to be installed. The ITM library ([tedaks/pyitm](https://github.com/tedaks/pyitm)) is bundled with this plugin.
This plugin also adapts code from [tedaks/nowires](https://github.com/tedaks/nowires) and [tedaks/ContourLines](https://github.com/tedaks/ContourLines); see [NOTICE.md](NOTICE.md) for third-party attribution and license details.

### Developer requirements

Only needed when running the test/lint/typecheck suite outside QGIS:

```bash
pip install -r requirements-test.txt       # pytest, pytest-cov, hypothesis, numpy, defusedxml
pip install -r requirements-typecheck.txt  # mypy, numpy
pip install -r requirements-lint.txt       # ruff
```

CI uses pinned versions from [constraints-ci.txt](constraints-ci.txt) — install with `pip install -c constraints-ci.txt -r requirements-test.txt` for parity.

## Installation

1. Copy the `NoWires` folder to your QGIS user plugins directory:
   - **Linux/macOS:** `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/`
   - **Windows:** `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\`

2. Restart QGIS and enable the plugin in **Plugins → Manage and Install Plugins**.

## Repository Layout

- `algorithm_p2p.py`: point-to-point ITM analysis
- `algorithm_coverage.py`: coverage heatmap analysis
- `algorithm_coverage_comparison.py`: coverage comparison producing a delta raster
- `algorithm_batch.py`: batch P2P analysis (one-to-many and many-to-one)
- `algorithm_contour.py`: contour line generation
- `base_algorithm.py`: shared base class for NoWires Processing algorithms
- `antenna.py`: antenna radiation pattern model with presets and pattern files
- `clutter.py`: terminal clutter correction dispatch and helpers
- `clutter_advanced.py`: advanced clutter mode dispatcher (saalos + P.2108 §3.1/§3.2 + P.2109 BEL)
- `clutter_categories.py`: clutter category definitions, WorldCover class mapping, P.2108 model dispatch params
- `clutter_constants.py`: shared clutter constants (simple loss table, limits)
- `clutter_context.py`: ClutterLossContext dataclass definition
- `cache_manager.py`: DEM and WorldCover tile cache cleanup utilities
- `clutter_p2108.py`: deprecation shim for legacy P.2108 callers
- `p2108_common.py`: shared inverse-normal CDF helpers and validation for P.2108/P.2109
- `p2108_height_gain.py`: ITU-R P.2108-1 §3.1 height-gain terminal correction
- `p2108_terrestrial_stat.py`: ITU-R P.2108-1 §3.2 statistical clutter loss for terrestrial paths
- `p2109_bel.py`: ITU-R P.2109-2 building entry loss
- `clutter_saalos.py`: saalos vegetation clutter loss (Python port from Rust)
- `coverage_engine.py`: coverage raster computation engine
- `coverage_compute.py`: shared coverage propagation helpers
- `coverage_analysis_params.py`: coverage algorithm parameter registration
- `coverage_params.py`: coverage parameter definitions and defaults
- `coverage_pool.py`: coverage multiprocessing pool and shared-memory management
- `coverage_tasks.py`: coverage per-pixel task definitions
- `coverage_summary.py`: raster-derived usable-distance metrics
- `coverage_palette.py`: heatmap stop definitions and coverage style renderer
- `coverage_legend.py`: coverage legend support in QGIS
- `coverage_opacity.py`: live coverage opacity dialog
- `coverage_reporting.py`: coverage report output helpers
- `coverage_dem_validate.py`: DEM coverage bounds validation helper for the coverage algorithm
- `comparison_add_params.py`: comparison algorithm parameter registration
- `comparison_panel.py`: single-panel comparison computation
- `comparison_params.py`: comparison parameter definitions
- `comparison_outputs.py`: comparison output helpers (vector + raster)
- `comparison_reporting.py`: comparison report output helpers
- `p2p_analysis_params.py`: P2P algorithm parameter registration
- `p2p_params.py`: P2P parameter definitions and defaults
- `p2p_compute.py`: P2P ITM and link-budget computation
- `p2p_outputs.py`: P2P vector output helpers
- `p2p_chart.py`: interactive profile chart with hover, callouts, and export
- `p2p_chart_format.py`: chart axis and label formatting
- `p2p_symbology.py`: P2P vector layer symbology
- `p2p_report_display.py`: P2P report display in QGIS
- `batch_analysis_params.py`: batch algorithm parameter registration
- `batch_params.py`: batch parameter definitions and defaults
- `batch_outputs.py`: batch output helpers
- `batch_writer.py`: batch CSV/layer writer
- `contour_generation.py`: contour line generation core
- `contour_overlay.py`: hillshade/elevation overlay helpers
- `contour_pipeline.py`: contour processing pipeline
- `contour_smoothing.py`: VRT Gaussian smoothing for contour DEM
- `contour_symbology.py`: rule-based contour symbology
- `radio.py`: ITM bridge, Fresnel analysis, signal-level definitions
- `fresnel.py`: Fresnel zone and LOS analysis
- `elevation.py`: DEM sampling, terrain profiles, ElevationGrid class
- `reliability.py`: formal-or-fallback availability and reliability helpers
- `report_export.py`: shared CSV/JSON/HTML report writers
- `report_pdf.py`: Qt-based PDF report writer (`QTextDocument` + `QPrinter`) used by Coverage Analysis
- `report_payloads.py`: pure-Python report payload and marker helpers
- `report_markers.py`: TX/RX marker output helpers
- `shared_params.py`: shared parameter registration helpers (including clutter/BEL params)
- `shared_dem_grid.py`: shared DEM grid download and cache management
- `constants.py`: shared numerical constants
- `defaults.py`: default parameter values
- `dem_downloader.py`: Copernicus GLO-30 DEM tile download, cache, merge, clip
- `worldcover_downloader.py`: ESA WorldCover 2020 tile download, cache, clip/merge
- `tile_download_base.py`: shared tile-downloader base class with retry and fsync
- `raster_io.py`: shared GeoTIFF writer
- `processing_utils.py`: QGIS Processing utility helpers
- `geo_bounds.py`: geographic bounds and padding helpers
- `nan_utils.py`: NaN-safe array utilities
- `temp_manager.py`: temporary directory management with cleanup
- `macos_compat.py`: macOS multiprocessing compatibility (find a real Python, set `PYTHONHOME` for spawned workers, validate via `_can_spawn`)
- `windows_compat.py`: Windows mirror of `macos_compat` — locates `pythonw.exe` (preferred) or `python.exe` in QGIS bundle layouts, validates each candidate, sets `PYTHONHOME` for spawned workers
- `antenna_pattern_preview.py`: standalone polar-plot dialog for previewing antenna pattern CSV files
- `overlay_raster.py`: overlay raster sizing helpers
- `three_d.py`: 3D layer tracking and scene helpers
- `provider.py`: NoWires Processing provider registration
- `nowires.py`: main plugin class and menu/toolbar actions
- `benchmarks/`: synthetic runtime benchmarks
- `itm/`: bundled ITM implementation
- `tests/`: regression and unit tests, including ITM reference-vector tests
- `metadata.txt`: QGIS plugin metadata

## Usage

Open the **Processing Toolbox** (`Ctrl+Alt+T`) and navigate to **NoWires**:

1. **Point-to-Point Analysis**: Select TX and RX points, configure frequency, antenna heights, and link parameters. Click Run to generate the link outputs, TX/RX markers, optional profile chart, and any requested reports.
2. **Batch P2P Analysis**: Select a TX point and a set of RX points (one-to-many), or an RX point and a set of TX points (many-to-one). Results are ranked by link margin.
3. **Coverage Analysis**: Select a TX point, set max analysis distance and grid resolution. Click Run to generate a signal-strength heatmap raster, coverage summary, and any requested reports.
4. **Coverage Comparison**: Run two coverage configurations side-by-side (Panel A and Panel B) and produce a delta raster showing path-loss difference in dB.
5. **Contour Lines**: Draw an extent, set contour interval and smoothing. Generates contour lines and optional hillshade.
6. **Coverage Opacity**: After running coverage, open the menu action to adjust the latest coverage raster opacity live.
7. **Open 3D View**: After running coverage or contours, open a tracked 3D scene from the plugin menu on Linux/macOS. On Windows, NoWires points you to the native QGIS 3D view.

## Data Source

Elevation data: **Copernicus GLO-30 Public DEM** hosted on AWS Open Data.
- Registry: https://registry.opendata.aws/copernicus-dem/
- Copernicus DEM © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

Land-cover data for automatic clutter correction: **ESA WorldCover 2020 v100**.
- Data access: https://esa-worldcover.org/en/data-access
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Attribution: © ESA WorldCover project / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium.

## Credits

- Radio propagation engine: [tedaks/pyitm](https://github.com/tedaks/pyitm) — NTIA Irregular Terrain Model (bundled)
- Original web application: [tedaks/nowires](https://github.com/tedaks/nowires)
- Contour lines algorithm: [ContourLines](https://github.com/tedaks/ContourLines) by Daniel Hulshof Saint Martin

## Development

The test suite in this repository is designed to run outside QGIS for fast regression checks.

### Run tests

```bash
pytest -q
```

The test suite includes ITM reference-vector tests (`tests/test_itm_reference_vectors.py`) that verify propagation primitives, edge cases for smooth earth diffraction, and end-to-end predict_p2p scenarios across all climate zones and boundary conditions.

### Typical local workflow

1. Make changes in the plugin source.
2. Run `pytest -q`.
3. Optionally run `python3 benchmarks/coverage_runtime.py` to compare runtime against the reference synthetic cases.
4. Copy the `NoWires` folder into your QGIS plugins directory for manual testing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution notes.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for notable project changes.

## Attribution

The advanced clutter model uses the saalos vegetation algorithm,
ported from ITWOM 3.0 (Sid Shumate, Givens & Bell, Inc.) via an
intermediate MIT-licensed Rust crate. See [NOTICE.md](NOTICE.md)
for the full upstream notice and MIT license text.

The P.2108-1 and P.2109-2 clutter and building entry loss models are
implemented from ITU-R Recommendations P.2108-1 (09/2021) and
P.2109-2 (08/2023). The inverse normal CDF approximation uses the
Abramowitz & Stegun §26.2.23 rational approximation with Newton
refinement via `math.erf`.

## License

SPDX-License-Identifier: GPL-3.0-or-later

GNU General Public License v3 or later.
Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>.
Third-party notices and upstream attribution details are documented in [NOTICE.md](NOTICE.md).
