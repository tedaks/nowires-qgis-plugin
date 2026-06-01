# NoWires Technical Documentation — v3.0.0

SPDX-License-Identifier: MIT

## Purpose

This document describes the NoWires plugin from a technical and implementation perspective. It is intended for developers, maintainers, and advanced users who need more detail than the user guide provides.

For installation and routine use, see [USERS-GUIDE.md](USERS-GUIDE.md).

## Scope

NoWires is a QGIS 4 plugin that combines:

- point-to-point radio propagation analysis
- area coverage heatmap analysis
- DEM download, caching, and clipping support

The runtime target is QGIS 4 with its bundled Qt 6 / PyQt 6 stack. The plugin does not include a Qt 5 compatibility layer; UI code should use Qt 6 API locations and scoped enum names directly.

## High-Level Architecture

The plugin is organized around QGIS Processing algorithms exposed by a custom provider.

### Entry Points

- [__init__.py](__init__.py)
  QGIS plugin entry hook
- [nowires.py](nowires.py)
  Main plugin class, menu/toolbar actions, Processing dialog launchers
- [provider.py](provider.py)
  Registers the NoWires Processing provider and algorithms

### Primary Algorithms

- [algorithm/p2p.py](algorithm/p2p.py)
  Point-to-point analysis
- [algorithm/coverage.py](algorithm/coverage.py)
  Coverage heatmap analysis

### Supporting Modules

- [radio.py](radio.py)
  ITM bridge, Fresnel analysis, signal-level definitions
- [fresnel.py](fresnel.py)
  Fresnel zone and LOS analysis
- [coverage/engine.py](coverage/engine.py)
  Coverage raster computation
- [coverage/compute.py](coverage/compute.py)
  Shared coverage propagation helpers
- [coverage/analysis_params.py](coverage/analysis_params.py)
  Coverage algorithm parameter registration
- [coverage/params.py](coverage/params.py)
  Coverage parameter definitions and defaults
- [coverage/pool.py](coverage/pool.py)
  Coverage multiprocessing pool and shared-memory management
- [coverage/_executor.py](coverage/_executor.py)
  Coverage multiprocessing executor (extracted from coverage_pool)
- [coverage/result_dispatch.py](coverage/result_dispatch.py)
  Batch result dispatch and failure logging (extracted from coverage_pool)
- [coverage/tasks.py](coverage/tasks.py)
  Per-pixel coverage task definitions
- [coverage/summary.py](coverage/summary.py)
  Raster-derived usable-distance metrics
- [coverage/palette.py](coverage/palette.py)
  Heatmap stop definitions
- [coverage/legend.py](coverage/legend.py)
  Coverage legend support in QGIS
- [coverage/opacity.py](coverage/opacity.py)
  Live opacity adjustment dialog for the latest coverage layer
- [coverage/reporting.py](coverage/reporting.py)
  Coverage report output helpers
- [reliability.py](reliability.py)
  Formal-or-fallback availability and reliability helpers
- [report/export.py](report/export.py)
  Shared CSV, JSON, and HTML report writers
- [report/payloads.py](report/payloads.py)
  Pure-Python payload builders and P2P marker helpers
- [report/markers.py](report/markers.py)
  TX/RX marker output helpers
- [elevation.py](elevation.py)
  DEM sampling, terrain profiles, geographic helpers
- [dem_downloader.py](dem_downloader.py)
  Copernicus GLO-30 download, cache, merge, clip
- [antenna.py](antenna.py)
  Directional antenna gain adjustment, presets, pattern files, and vertical downtilt
- [clutter/__init__.py](clutter/__init__.py)
  Terminal clutter correction dispatch and helpers
- [clutter/advanced.py](clutter/advanced.py)
  Advanced clutter mode dispatcher (P.833-9 §2.1 + P.2108 §3.1/§3.2 + P.2109 BEL)
- [clutter/categories.py](clutter/categories.py)
  Clutter category definitions, WorldCover class mapping, P.2108 model dispatch params
- [clutter/constants.py](clutter/constants.py)
  Retained for compatibility; `MAX_CLUTTER_LOSS` removed in v2.0.0
- [clutter/context.py](clutter/context.py)
  ClutterLossContext dataclass
- [clutter/grid.py](clutter/grid.py)
  LandCoverGrid class for WorldCover raster sampling
- [clutter/resolve.py](clutter/resolve.py)
  Clutter resolution logic (grid acquisition and category dispatch)
- [cache_manager.py](cache_manager.py)
  DEM and WorldCover tile cache cleanup utilities
- [clutter/p2108_common.py](clutter/p2108_common.py)
  Shared inverse-normal CDF helpers (`Q⁻¹`, `F⁻¹`) and validation for P.2108/P.2109
- [clutter/p2108_height_gain.py](clutter/p2108_height_gain.py)
  ITU-R P.2108-1 §3.1 height-gain terminal correction (scalar + vectorized)
- [clutter/p2108_terrestrial_stat.py](clutter/p2108_terrestrial_stat.py)
  ITU-R P.2108-1 §3.2 statistical clutter loss for terrestrial paths (scalar + vectorized)
- [clutter/p2109_bel.py](clutter/p2109_bel.py)
  ITU-R P.2109-2 building entry loss (scalar + vectorized)
- [clutter/p833.py](clutter/p833.py)
  ITU-R P.833-9 §2.1 vegetation clutter loss (Am formula, scalar + vectorised)
- [worldcover_downloader.py](worldcover_downloader.py)
  ESA WorldCover 2020 v100 tile download, caching, and clip/merge
- [overlay_raster.py](overlay_raster.py)
  Overlay raster sizing helpers
- [three_d.py](three_d.py)
  3D layer tracking and scene-opening helpers
- [base_algorithm.py](base_algorithm.py)
  Shared base class for NoWires Processing algorithms
- [constants.py](constants.py)
  Shared numerical constants
- [defaults.py](defaults.py)
  Default parameter values
- [shared_params.py](shared_params.py)
  Shared parameter registration helpers (including clutter/BEL params)
- [shared_dem_grid.py](shared_dem_grid.py)
  Shared DEM grid download and cache management
- [raster_io.py](raster_io.py)
  Shared GeoTIFF writer
- [processing_utils.py](processing_utils.py)
  QGIS Processing utility helpers
- [geo_bounds.py](geo_bounds.py)
  Geographic bounds and padding helpers
- [nan_utils.py](nan_utils.py)
  NaN-safe array utilities
- [_bilinear.py](_bilinear.py)
  Shared bilinear interpolation (scalar, line, grid paths)
- [_geo_utils.py](_geo_utils.py)
  Geography utility helpers
- [temp_manager.py](temp_manager.py)
  Temporary directory management with cleanup
- [macos_compat.py](macos_compat.py)
  macOS multiprocessing compatibility (locates a real Python interpreter,
  validates it via `_can_spawn`, sets `PYTHONHOME` for spawned workers)
- [windows_compat.py](windows_compat.py)
  Windows mirror of `macos_compat`: locates `pythonw.exe` (preferred) or
  `python.exe` in QGIS bundle layouts, validates each candidate, sets
  `PYTHONHOME` for spawned workers, honours `NOWIRES_PYTHON_EXE`
- [antenna_pattern_preview.py](antenna_pattern_preview.py)
  Standalone polar-plot dialog for previewing antenna pattern CSV files,
  reached via the *NoWires → Preview Antenna Pattern* menu entry
- [tile_download_base.py](tile_download_base.py)
  Shared tile-downloader base class with retry and fsync
- [p2p/compute.py](p2p/compute.py)
  P2P ITM and link-budget computation
- [p2p/params.py](p2p/params.py)
  P2P parameter definitions and defaults
- [p2p/analysis_params.py](p2p/analysis_params.py)
  P2P algorithm parameter registration
- [p2p/outputs.py](p2p/outputs.py)
  P2P vector output helpers
- [p2p/outputs_internal.py](p2p/outputs_internal.py)
  P2P output layer and report writing (extracted from compute.py)
- [p2p/chart.py](p2p/chart.py)
  Interactive profile chart with hover, callouts, and export
- [p2p/chart_helpers.py](p2p/chart_helpers.py)
  Chart helper functions extracted from chart.py
- [p2p/chart_format.py](p2p/chart_format.py)
  Chart axis and label formatting
- [p2p/symbology.py](p2p/symbology.py)
  P2P vector layer symbology
- [p2p/report_display.py](p2p/report_display.py)
  P2P report display in QGIS
- [batch/analysis_params.py](batch/analysis_params.py)
  Batch algorithm parameter registration
- [batch/params.py](batch/params.py)
  Batch parameter definitions and defaults
- [batch/outputs.py](batch/outputs.py)
  Batch output helpers
- [batch/writer.py](batch/writer.py)
  Batch CSV/layer writer
- [comparison/add_params.py](comparison/add_params.py)
  Comparison algorithm parameter registration
- [comparison/params.py](comparison/params.py)
  Comparison parameter definitions and defaults
- [comparison/panel.py](comparison/panel.py)
  Single-panel comparison computation
- [comparison/outputs.py](comparison/outputs.py)
  Comparison output helpers (vector + raster)
- [comparison/reporting.py](comparison/reporting.py)
  Comparison report output helpers

### Bundled Third-Party Engine

- [itm/](itm)
  Bundled ITM implementation adapted from `tedaks/pyitm`

## Plugin Lifecycle

1. QGIS loads the plugin.
2. `NoWiresPlugin.initGui()` registers the Processing provider and adds menu/toolbar actions.
3. User launches an algorithm either from the menu or the Processing toolbox.
4. The selected algorithm collects parameters and executes.
5. Output layers are added to the map if valid.
6. Optional menu actions can adjust the latest coverage layer opacity or open a tracked 3D view.

## Processing Provider

The NoWires provider currently exposes:

- `p2p_analysis`
- `coverage_analysis`
- `coverage_comparison`
- `batch_p2p_analysis`

## Data Sources

### DEM Source

NoWires uses Copernicus GLO-30 DEM tiles hosted on AWS Open Data.

- Base URL is defined in [dem_downloader.py](dem_downloader.py)
- tiles are Cloud-Optimized GeoTIFFs
- tiles are cached locally under a NoWires temp directory

### Cache Behavior

- cached tiles are reused on later runs
- download retries are implemented
- tile names are validated against a regex
- temporary `.tmp` files are cleaned up on failure paths where possible

## Menu Actions Outside Processing

In addition to Processing algorithms, the plugin exposes post-run helper actions from the `NoWires` menu:

- `Point-to-Point Analysis`
  Launches the P2P algorithm dialog
- `Coverage Analysis`
  Launches the coverage algorithm dialog
- `Coverage Opacity`
  Opens a non-modal slider dialog for the latest tracked coverage layer
- `Open 3D View`
  Opens a QGIS 3D scene from the latest tracked NoWires DEM and coverage layers when supported by the runtime platform
- `Coverage Comparison`
  Launches the coverage comparison algorithm dialog
- `Batch P2P Analysis`
  Launches the batch P2P algorithm dialog
- `Clear DEM Cache`
  Removes stale downloaded DEM and WorldCover tiles from the local cache

## Point-to-Point Analysis

### Purpose

`algorithm/p2p.py` computes a single ITM link between a transmitter and receiver and then performs Fresnel-zone and earth-curvature analysis on the sampled terrain profile.

### P2P Flow

1. Read TX and RX points in EPSG:4326.
2. Compute link distance.
3. Download and prepare a DEM covering the path with padding.
4. Build a terrain profile using `ElevationGrid.terrain_profile()`.
5. Convert terrain elevations to ITM PFL format.
6. Run ITM path-loss prediction through `itm_p2p_loss()`.
7. Run Fresnel/LOS analysis in `fresnel_profile_analysis()`.
8. Compute link-budget values.
9. Write vector outputs, optional reports, and optional chart.

### P2P Outputs

Point-to-point analysis now produces (all layers persist across QGIS sessions):

- profile line output
- Fresnel zone output
- TX/RX marker output (persistent)
- optional interactive profile chart (hover callouts, Fresnel toggle, export)
- optional `CSV`, `JSON`, and `HTML` reports

Point-to-point reports carry reliability and clutter fields:

- `availability_method`
- `availability_estimate_pct`
- `fade_margin_class`
- `reliability_summary`
- `clutter_source`
- `clutter_method`
- `clutter_percentile`
- `clutter_tx_db`
- `clutter_rx_db`
- `tx_cch_m`
- `rx_cch_m`
- `total_path_loss_db`
- `bel_rx_db`

### P2P Parameters

#### Main propagation inputs

- TX point
- RX point
- TX height
- RX height
- frequency
- polarization
- climate
- time percentage
- location percentage
- situation percentage
- TX power
- TX gain
- RX gain
- cable loss
- RX sensitivity
- Earth radius factor (`k`) preset — also sets surface refractivity `N0`
- Decouple `N0` from k-factor preset (boolean; restores Fresnel-display-only `k`)

#### Advanced inputs

- custom Earth radius factor (`K_FACTOR`)
- `N0` (overridden by the k-factor preset unless decoupled)
- `epsilon`
- `sigma`
- antenna preset, azimuth, beamwidth, front-to-back ratio, downtilt, and optional pattern CSV files
- clutter model (Off / Simple clutter correction / Advanced clutter correction)
- clutter raster path (optional; auto-downloads WorldCover when clutter is enabled and left blank)
- TX clutter override
- RX clutter override
- canopy/clutter height override (CCH_OVERRIDE) for advanced mode
- clutter percentile (0.01–99.99) for P.2108 §3.2 and P.2109
- street width (5–100 m, default 27) for P.2108 §3.1
- BEL enabled (boolean) for P.2109 building entry loss
- BEL building type (Traditional / Thermally-efficient) for P.2109
- BEL elevation angle (0–90°, default 0) for P.2109

### Earth Radius Factor Handling

Visible presets and their coupled surface refractivity `N0` (since v2.0.0):

| Preset | `k` | Coupled `N0` (N-units) |
|--------|-----|------------------------|
| `0.67 - Sub-refractive`         | 0.67 | 250 |
| `1.00 - Geometric`              | 1.00 | 280 |
| `1.33 - Standard atmosphere`    | 1.33 | 301 |
| `2.00 - Super-refractive`       | 2.00 | 350 |
| `4.00 - Strong super-refractive`| 4.00 | 400 |
| `Custom`                        | numeric `K_FACTOR` | user `N0` (free) |

Default: `1.33 - Standard atmosphere`, which couples to `N0 = 301`
(`DEFAULT_N0`), so the out-of-box default is numerically unchanged from earlier
releases.

The mapping table (`K_FACTOR_PRESET_N0`) and the resolvers
(`resolve_k_factor`, `resolve_n0`) live in `k_factor_presets.py` and are
re-exported from `radio` for backward-compatible imports.

**N0 coupling (default change in v2.0.0):** selecting a non-Custom preset now
overrides the surface refractivity `N0`, so the preset changes the ITM
propagation prediction — not only the Fresnel/LOS earth-bulge display. The
sub-/super-refractive `N0` values are representative planning values spanning
the valid `[250, 400]` N-unit band; the standard preset is pinned to
`DEFAULT_N0` so existing default-preset runs are unaffected. When a preset
overrides the user's `N0`, the algorithm pushes a feedback note stating the new
value and how to opt out. The coupling is applied in the P2P and Batch
algorithm readers (`algorithm/p2p.py`, `algorithm/batch.py`).

Keeping `N0` independent of `k` (the pre-v2.0.0 behavior):

- enable the **Decouple N0 from k-factor preset** checkbox — the preset then
  affects only the Fresnel/earth-bulge display and `N0` is taken from the field
  as entered; or
- choose the **Custom** preset, which uses the numeric `K_FACTOR` and likewise
  leaves `N0` under direct user control.

Backward compatibility:

- the older numeric `K_FACTOR` parameter is still present as an advanced field
- if an older Processing model supplies `K_FACTOR` without the new preset
  parameter, the numeric value is still honored
- a Processing model that predates the `DECOUPLE_N0` parameter defaults it to
  `False` (coupling on); add the parameter or switch to Custom to restore the
  old `N0`-independent behavior

### How `k` and the Preset Affect Each Analysis

The Earth-radius factor `k` drives the Fresnel and earth-bulge visualization in
point-to-point analysis. Since v2.0.0 the **preset** additionally sets `N0`,
which feeds the ITM propagation calculation in **both P2P and Batch**. Coverage
analysis exposes neither the preset nor `k` (it sets `N0` directly), so coverage
behavior is unchanged.

## Coverage Analysis

### Purpose

`algorithm/coverage.py` produces a received-signal raster and derives usable-range metrics from that raster.

### Coverage Flow

1. Read the transmitter point and user inputs.
2. Treat `Max analysis distance (km)` as the outer computation envelope.
3. Download and prepare a DEM covering that envelope.
4. Build a dense elevation grid.
5. Call `compute_coverage()` in [coverage/engine.py](coverage/engine.py).
6. Write the result to a GeoTIFF.
7. Apply a heatmap renderer and opacity setting.
8. Add the raster and legend to the map.
9. Compute raster-derived range metrics from cells above sensitivity.
10. Optionally write `CSV`, `JSON`, and `HTML` report files from the computed summary values.

Coverage reports now also include reliability guidance and clutter loss breakdown:

- `fade_margin_class`
- `availability_method`
- `availability_estimate_pct` when the formal path is used
- `reliability_summary`
- `clutter_source`
- `clutter_method`
- `clutter_percentile`
- `clutter_tx_db`
- `clutter_rx_db`
- `itm_loss_db` (grid-wide mean over valid pixels)
- `total_path_loss_db` (grid-wide mean over valid pixels)
- `bel_rx_db`

### Max Analysis Distance vs Actual Coverage

This is an important product distinction:

- `Max analysis distance (km)` defines how far the algorithm searches
- it is not the predicted service radius
- usable range is derived from raster cells where `Prx >= RX sensitivity`

### Coverage Parameters

#### Core analysis inputs

- TX point
- TX and RX heights
- frequency
- max analysis distance
- grid size resolution
- overlay transparency
- polarization
- climate
- time percentage
- location percentage
- situation percentage
- TX power
- TX gain
- RX gain
- cable loss
- RX sensitivity
- antenna azimuth and beamwidth
- antenna preset, front-to-back ratio, downtilt, and optional pattern CSV files
- clutter model (Off / Simple clutter correction / Advanced clutter correction)
- clutter raster path (optional; auto-downloads WorldCover when clutter is enabled and left blank)
- TX clutter override
- RX clutter override
- canopy/clutter height override (CCH_OVERRIDE) for advanced mode
- clutter percentile (0.01–99.99) for P.2108 §3.2 and P.2109
- street width (5–100 m, default 27) for P.2108 §3.1
- BEL enabled (boolean) for P.2109 building entry loss
- BEL building type (Traditional / Thermally-efficient) for P.2109
- BEL elevation angle (0–90°, default 0) for P.2109

#### Advanced inputs

- `N0`
- `epsilon`
- `sigma`

### Grid Resolution

Current presets:

- `64 x 64`
- `128 x 128`
- `192 x 192`
- `256 x 256`
- `384 x 384`
- `512 x 512`
- `768 x 768`
- `1024 x 1024`

Tradeoff:

- larger grids provide smoother-looking rasters
- larger grids increase ITM path computations and runtime

### Coverage Engine Details

`coverage/engine.py` is responsible for per-pixel propagation computation.

Key behaviors:

- output grids are initialized as `float32`
- computations are limited to the requested envelope
- each pixel samples a terrain path between TX and cell center
- antenna directionality is applied through `antenna_gain_factor()` and `antenna_gain_adjustment_db()`

### Antenna Pattern Layer

`antenna.py` provides directional gain adjustment on top of the user-specified peak antenna gain. The adjustment is a *relative* offset — boresight is `0 dB` and off-axis directions are negative, so the adjustment is subtracted from the link budget.

#### Presets

| Preset | Key | H Beamwidth | V Beamwidth | Front-Back Ratio |
|---|---|---|---|---|
| Omni | `omni` | 360° | 360° | 0 dB |
| Sector 90 | `sector_90` | 90° | 10° | 25 dB |
| Sector 120 | `sector_120` | 120° | 10° | 25 dB |
| Dish 20 | `dish_20` | 20° | 8° | 35 dB |
| Custom | `custom` | configurable | configurable | 25 dB |

The `Omni` preset produces `0 dB` adjustment everywhere and preserves legacy behaviour. Sector and Dish presets provide common planning shapes with configurable azimuth, front-to-back ratio, and downtilt.

#### Horizontal Pattern

When a horizontal pattern CSV file is supplied, gain is interpolated from the file with 360° wraparound. Otherwise, a simplified parabolic model is used:

- Within the half-beamwidth: `gain = -3 * x²` where `x` is the normalized angular offset from boresight (`-1` to `+1` across the half-beamwidth).
- Outside the half-beamwidth: `gain = -front_back_db`.

The horizontal bearing is computed as the angle difference between the target direction and the antenna azimuth, normalised to `[-180°, +180°]`.

#### Vertical Pattern

When a vertical pattern CSV file is supplied, gain is interpolated from the file, clamped to the file's angle range (no wrapping). Otherwise, the same parabolic model is used with `downtilt_deg` shifting the main beam downward:

- Within the half-beamwidth: `gain = -3 * x²` where `x = (elevation_angle + downtilt) / (vertical_beamwidth / 2)`.
- Outside the half-beamwidth: `gain = -12 dB`.

#### Combined Adjustment

The final `antenna_gain_adjustment_db = min(0, horizontal + vertical)`. Clamping at `0 dB` ensures the adjustment never adds gain beyond the user-specified peak.

#### Pattern CSV Files

Pattern CSVs use two numeric columns:

```csv
angle_deg,gain_adjust_db
0,0
90,-12
180,-30
270,-12
360,0
```

Horizontal pattern files wrap around 360° (the last point must close the circle). Vertical pattern files are clamped to the file's angle range. Cache is provided by `_read_pattern_points()` with an LRU cache of 32 entries.

#### Application in Algorithms

- **Coverage**: `antenna_gain_adjustment_db()` is called per pixel using the bearing from TX to each cell centre and the vertical elevation angle, producing a directional coverage heatmap.
- **P2P**: TX and RX pattern adjustments are computed using forward and reverse bearings plus the endpoint vertical angles.

### Clutter Correction Layer

`clutter/__init__.py` implements the optional terminal correction layer. It keeps ITM unchanged, samples a WorldCover-compatible raster at terminal locations, maps raw classes to propagation categories, and adds terminal losses after ITM.

Three clutter modes are available:

- **Off** — no terminal clutter correction.
- **Simple clutter correction** — flat per-category losses (legacy behaviour).
- **Advanced clutter correction** — ITU-R P.833-9 §2.1 Am vegetation model for vegetation categories; ITU-R P.2108 site-general clutter loss for built and rural categories. Uses antenna height and frequency. If the antenna is at or above the canopy/clutter height, the model gates the loss to zero for that terminal.

Key helpers:

- `compute_terminal_clutter_losses()`: resolves TX and RX clutter categories (from override, raster sample, or `open` fallback) and returns a `TerminalClutterLosses` dataclass with `tx_loss_db`, `rx_loss_db`, `total_loss_db`, `tx_cch_m`, `rx_cch_m`, and a `source` label.
- `clutter_source_label()`: builds a user-visible source string for reports (e.g. `"override,/tmp/worldcover.vrt"` or `"fallback_open"`).
- `clutter_override_value()`: converts a Processing parameter index or category string into a category name or `None`.

### ClutterLossContext

`ClutterLossContext` is a dataclass that bundles the inputs required by the advanced clutter models. Its fields are:

| Field | Type | Description |
|---|---|---|
| `model` | `ClutterModel` | Clutter model in use (`"simple"` or `"advanced"`) |
| `frequency_mhz` | `float` | Frequency in MHz |
| `distance_m` | `float` | Path distance (m) |
| `tx_height_m` | `float` | TX antenna height above ground (m) |
| `rx_height_m` | `float` | RX antenna height above ground (m) |
| `cch_override_m` | `float \| None` | Canopy/clutter height override (m); `None` means no override |
| `percentile` | `float` | Location percentile (0.01–99.99) for P.2108 §3.2 and P.2109 BEL |
| `street_width_m` | `float` | Street width (m) for P.2108 §3.1 (default 27) |
| `bel_enabled` | `bool` | Whether P.2109 building entry loss is enabled |
| `bel_building_type` | `str` | Building type for P.2109 (`traditional` or `thermally_efficient`) |
| `bel_elevation_angle_deg` | `float` | Elevation angle at façade (°) for P.2109 (default 0) |

### Advanced Clutter Models

The advanced mode selects between four internal models based on the clutter category and frequency, per the ITU-R P.2108-1 and P.2109-2 specifications:

1. **None** (`open` category) — returns 0.0 dB loss. Open areas have no applicable clutter model.
2. **P.2108 §3.1 height-gain** (`open_rural` and `dense_rural` categories) — ITU-R P.2108-1 §3.1 height-gain terminal correction for frequencies 0.03–3 GHz. Uses method (2b) for open/rural categories, computing a height-gain correction based on antenna height, representative clutter height R, frequency, and street width. Not a function of distance or percentile. Returns 0.0 dB for antennas at or above the representative clutter height R.
3. **P.2108 §3.1 + §3.2 combined** (`suburban` and `urban` categories) — applies both the §3.1 height-gain correction and the §3.2 statistical clutter loss, taking the maximum of the two in the overlap band (0.5–3 GHz). Above 3 GHz, only §3.2 applies. The §3.2 model is a combined urban+suburban statistic (not per-category) and is percentile-based with a 2 km distance cap.
4. **P.833-9 §2.1 Am** (`vegetation` category) — maximum woodland attenuation Am from ITU-R Recommendation P.833-9 §2.1, using the St. Petersburg fit (A1=1.37, α=0.42, valid 105.9–2117.5 MHz). Am is the d→∞ asymptote of the general Eq. 1 and is designated by the document as "equivalent to the clutter loss often quoted for a terminal obstructed by some form of ground cover or clutter." Returns 0.0 dB when the antenna is at or above the canopy height.

The frequency-based dispatch table (per P.2108/P.2109 compliance design §6):

| Category | f < 0.5 GHz | 0.5 ≤ f ≤ 3 GHz | 3 < f ≤ 67 GHz | f > 67 GHz |
|---|---|---|---|---|
| open | 0 | 0 | 0 | 0 |
| open_rural | §3.1 | §3.1 | 0 | 0 |
| dense_rural | §3.1 | §3.1 | 0 | 0 |
| vegetation | P.833 Am | P.833 Am | P.833 Am | P.833 Am |
| suburban | §3.1 | §3.1 + §3.2 (max) | §3.2 | §3.2 (clamped) |
| urban | §3.1 | §3.1 + §3.2 (max) | §3.2 | §3.2 (clamped) |

For suburban/urban in the overlap band (0.5–3 GHz), both §3.1 and §3.2 are computed and the larger value is used — they model different physical effects (terminal-local height-gain vs path-statistical clutter).

Out-of-band frequencies are clamped to the nearest valid range, with a warning logged once per session.

### P.2108-1 §3.1 — Height-Gain Terminal Correction

`clutter/p2108_height_gain.py` implements the ITU-R P.2108-1 §3.1 height-gain terminal correction.

- **Validity:** 0.03–3 GHz, antenna height h below representative clutter height R.
- Per-category** (from P.2108-1 Table 3): categories `open`, `open_rural`, and `dense_rural` use method (2b) -- `Ah = -Kh2 * log10(h/R)`; categories `suburban`, `urban`, and `vegetation` use method (2a) -- `Ah = J(v) - 6.03` with knife-edge diffraction `J(v)`.
- **Not a function of distance or percentile** — depends only on h, f, R, and street width w_s.
- **Gated to zero** when antenna height ≥ representative clutter height R.

API: `height_gain_loss(h_m, f_ghz, category, w_s_m=27.0)` returns loss in dB.

### P.2108-1 §3.2 — Statistical Clutter Loss

`clutter/p2108_terrestrial_stat.py` implements the ITU-R P.2108-1 §3.2 statistical clutter loss for terrestrial paths.

- **Validity:** 0.5–67 GHz, percentage locations 0 < p < 100.
- **Combined urban+suburban statistic** — not per-category. Caller is responsible for only invoking this for urban/suburban categories.
- **Percentile-based:** lower percentile → lower loss (loss not exceeded for that percentage of locations).
- **Distance cap:** loss is capped at the value for d = 2 km (Eq. (6)).
- Uses `Q⁻¹` (inverse complementary normal CDF): `Q⁻¹(α) = −F⁻¹(α)`, opposite sign convention to P.2109's `F⁻¹`.

API: `clutter_loss_p2108_terrestrial_stat(d_km, f_ghz, p=50.0)` returns loss in dB.

### P.2109-2 — Building Entry Loss

`clutter/p2109_bel.py` implements the ITU-R P.2109-2 building entry loss model.

- **Validity:** 0.08–100 GHz, building type `traditional` or `thermally_efficient`, elevation angle θ (degrees above horizontal), probability P (0–100%).
- **Two-lognormal model** (P.2109-2 §3, eqs (1)–(10)): `L_BEL(P) = 10·log10(10^(0.1·A) + 10^(0.1·B) + 10^(0.1·C))` where A and B are lognormal terms and C = −3.0 dB is a constant floor.
- **Elevation-angle term** `L_e = 0.212·|θ|` adds loss proportional to elevation at the building façade (default 0° = horizontal incidence).
- **No floor-penetration term** — P.2109 does not model floor penetration; this was a v1 design error.
- Uses `F⁻¹` (regular inverse normal CDF), opposite sign convention to P.2108's `Q⁻¹`.
- Applied to RX terminal only when `BEL_ENABLED=True`.

API: `building_entry_loss(f_ghz, building_type, theta_deg=0.0, p=50.0)` returns loss in dB.

### P.2108/P.2109 Shared Helpers

`clutter/p2108_common.py` provides:

- `_ndtri(p)` — Abramowitz & Stegun §26.2.23 rational approximation with 2 Newton refinement steps using `math.erf`. Avoids scipy dependency.
- `q_inv_complementary_normal(p)` — `Q⁻¹(p) = −F⁻¹(p)` (P.2108/§3.2 convention).
- `f_inv_normal(p)` — regular `F⁻¹(p)` (P.2109 convention).
- `validate_frequency_ghz(f, f_min, f_max)` — clamps and warns on out-of-band frequencies.
- `validate_distance_km(d, d_min)` — clamps and warns on short distances.

#### Decision D9: P.833 Vegetation Clutter

The P.833-9 §2.1 Am formula uses antenna height and frequency only. The woodland boundary to receiver depth `d` (required for the general Eq. 1) is not available from the land-cover raster, so Am (the d→∞ limit, explicitly designated as clutter loss) is applied directly. If the antenna height is at or above the canopy height, the loss is gated to 0.0 dB.

### P.833-9 §2.1 — Vegetation Clutter Loss (Am)

Located in `clutter/p833.py`. Implements the maximum woodland attenuation
formula from ITU-R P.833-9 §2.1 Eq. 2:

```
Am = 1.37 × f⁰·⁴²  (St. Petersburg fit, valid 105.9–2117.5 MHz)
```

Extrapolation outside the validated range is not sanctioned by the document.

**API:**

- `clutter_loss_p833(cch_m: float, h_rx_m: float, f_mhz: float) -> float` —
  returns Am when `h_rx_m < cch_m`, 0.0 otherwise (scalar, no numpy import).
- `clutter_loss_p833_vec(cch_m, h_rx_m, f_mhz) -> np.ndarray` —
  vectorised variant with lazy numpy import; inputs broadcast to a common shape.

### TerminalClutterLosses

`TerminalClutterLosses` is a dataclass returned by `compute_terminal_clutter_losses()`. Its fields are:

| Field | Type | Description |
|---|---|---|
| `tx_category` | `str` | TX clutter category |
| `rx_category` | `str` | RX clutter category |
| `tx_loss_db` | `float` | TX terminal clutter loss (dB) |
| `rx_loss_db` | `float` | RX terminal clutter loss (dB) |
| `total_loss_db` | `float` | Sum of TX and RX clutter losses (dB) |
| `source` | `str` | Descriptive label for the clutter data source |
| `tx_cch_m` | `float` | Effective canopy/clutter height used at TX (m) |
| `rx_cch_m` | `float` | Effective canopy/clutter height used at RX (m) |
| `tx_bel_db` | `float` | TX building entry loss (always 0.0 — TX is outdoor) |
| `rx_bel_db` | `float` | RX building entry loss (dB, P.2109-2; 0.0 when BEL not enabled) |
| `total_with_bel_db` | `float` | Total clutter + BEL: `total_loss_db + rx_bel_db` |
| `method` | `str` | Which sub-model fired (e.g. `"§3.1+§3.2/p833"`) |
| `percentile` | `float` | Location percentile used for §3.2 and BEL |

The `method` field identifies which clutter sub-models were applied for TX and RX. Examples:
- `"none/none"` for open terrain on both terminals
- `"§3.1/§3.1+§3.2"` for open_rural TX and urban RX
- `"p833/p833"` for vegetation on both terminals

The `tx_cch_m` and `rx_cch_m` fields are included in P2P report payloads. For simple mode, these are always 0.0. For advanced mode, they reflect the canopy height used in the P.833 or P.2108 computation.

Key helpers:

- `LandCoverGrid.from_raster()`: loads a land-cover GeoTIFF into a `LandCoverGrid` with geographic bounds and no-data handling.
- `LandCoverGrid.sample_category()`: samples the grid at a given lat/lon and returns a clutter category string.
- `ensure_clutter_grid_for_area()`: auto-downloads WorldCover tiles when clutter is enabled and no raster is supplied.

Simple mode clutter categories and loss table (five categories; advanced-mode
categories `open_rural` and `dense_rural` remap to `rural` and `vegetation`
respectively via `remap_simple_category`):

| Category | Loss (dB) |
|---|---|
| open | 0.0 |
| rural | 2.0 |
| vegetation | 6.0 |
| suburban | 8.0 |
| urban | 10.0 |

Advanced mode category dispatch (per P.2108/P.2109 compliance design §6):

| Category | Model | P.2108 §3.1 Method | R (m) | §3.2 Applicable |
|---|---|---|---|---|
| open | none | — | — | no |
| open_rural | p2108_height_gain | (2b) | 10 | no |
| dense_rural | p2108_height_gain | (2b) | 10 | no |
| vegetation | p833 | — | — | no |
| suburban | p2108_combined | (2a) | 10 | yes |
| urban | p2108_combined | (2a) | 20 | yes |

WorldCover class-to-category mapping (`worldcover_class_to_clutter_category` for simple mode, `worldcover_class_to_advanced_category` for advanced mode):

Simple mode:

| WorldCover class | Category |
|---|---|
| 10, 95 | vegetation |
| 20, 30, 40, 100 | rural |
| 50 | urban |
| 60, 70, 80, 90 | open |

Advanced mode splits `rural` into `open_rural` (classes 30, 40) and `dense_rural` (classes 20, 100), with classes 10, 95 mapping to `vegetation`, class 50 to `urban`, and classes 60, 70, 80, 90 to `open` as in simple mode.

### Clutter Reporting

Both P2P and coverage reports expose clutter loss breakdown:

- `clutter_source`: a descriptive label produced by `clutter_source_label()` rather than a raw file path.
- `clutter_method`: which clutter sub-model fired (e.g. `"§3.1/§3.1+§3.2"` or `"p833/none"`).
- `clutter_percentile`: the location percentile used for §3.2 and BEL calculations.
- `clutter_tx_db`: TX terminal clutter loss (dB).
- `clutter_rx_db`: RX terminal clutter loss (dB).
- `tx_cch_m`: effective canopy/clutter height used at TX (m). Always 0.0 in simple mode.
- `rx_cch_m`: effective canopy/clutter height used at RX (m). Always 0.0 in simple mode.
- `total_path_loss_db`: `itm_loss_db + clutter_tx_db + clutter_rx_db` (clutter only, no BEL).
- `bel_rx_db`: RX building entry loss from P.2109-2 (0.0 when BEL not enabled).
- `total_with_bel_db`: `total_path_loss_db + bel_rx_db` (clutter + BEL).

For coverage reports, `itm_loss_db` and `total_path_loss_db` are grid-wide means over valid pixels, `clutter_tx_db` is the TX terminal loss at the transmitter location, and `clutter_rx_db` is derived as `clutter_total_mean - clutter_tx_db`.

For P2P reports, clutter losses are computed per terminal using `compute_terminal_clutter_losses()` and included directly.

### Output Persistence

Coverage analysis writes a persistent TX marker layer ("Coverage TX") to the user's
NoWires data directory, alongside the coverage raster. Both layers stay in the map
project between QGIS sessions. The marker shapefile is written to
`NoWires-<user>/coverage_prx/tx_marker.shp`. P2P outputs are similarly written to
`NoWires-<user>/p2p_outputs/` and remain available across sessions.

### Multiprocessing Note

- All three desktop platforms (Linux, macOS, Windows) use a `ProcessPoolExecutor` worker pool with shared memory by default. The decision is gated by `coverage_pool.should_use_multiprocessing()`, which consults a platform-specific *validating* helper:
  - **Linux**: assumed to work; no further checks.
  - **macOS**: `macos_compat.find_macos_python_executable()` searches for a real Python interpreter (the QGIS launcher binary at `sys.executable` cannot be used because spawning it relaunches the QGIS GUI), then validates each candidate by actually launching it with `PYTHONHOME=sys.prefix`. The bundled QGIS-on-macOS `python3.12` has its `sys.prefix` baked to a CI builder path that doesn't exist on user machines; setting `PYTHONHOME` in the parent env lets spawned workers find the QGIS-bundled stdlib.
  - **Windows**: `windows_compat.find_windows_python_executable()` mirrors the macOS helper. It prefers `pythonw.exe` over `python.exe` (so each spawned worker doesn't pop a stray cmd window) and probes common bundle layouts (`<qgis>/pythonw.exe`, `<qgis>/../apps/Python3X/pythonw.exe`, `<qgis>/bin/pythonw.exe`, etc.).
- If the validating helper returns `None` on macOS or Windows, the executor logs a clear warning and falls back to single-threaded mode cleanly.
- The `NOWIRES_PYTHON_EXE` env var explicitly overrides interpreter detection on both macOS and Windows (e.g. point at `/opt/homebrew/bin/python3.12` or `C:\Python312\pythonw.exe`).
- The `NOWIRES_MAX_WORKERS` env var caps worker count (default `min(os.cpu_count(), 16)`).
- The `NOWIRES_WINDOWS_MP=1` env-var opt-in present in v1.5.3 is **removed in v1.5.5**; the new validating helper is the gate.
- No cross-process cancel signal is used. Cancellation flows from the main thread breaking out of `pool.map` between batches; in-flight batches finish naturally (~64 tasks × ~5 ms ≈ 320 ms worst-case wait at default chunk size). Earlier attempts to share a cancel signal via `multiprocessing.Event()` and `multiprocessing.Manager().Event()` both broke on macOS QGIS under spawn-mode pickling.
- The functions handed to `ProcessPoolExecutor` (`_init_cov_pool` as `initializer`, `_itm_worker_batch` as the `pool.map` callable) are resolved by a **function-local** `from .coverage_pool import _init_cov_pool, _itm_worker_batch` inside `execute_coverage_tasks`, not by a module-scope import in `coverage/_executor.py`. Reason: `pickle` verifies a function reference by `getattr(sys.modules[fn.__module__], fn.__qualname__) is fn`. A module-scope import freezes the reference to whichever function object existed the *first* time `coverage/_executor.py` loaded; if `NoWires.coverage_pool` is later replaced in `sys.modules` (QGIS plugin reload, the "Plugin Reloader" plugin, any `importlib.reload` of just that file) the cached reference diverges from the current module's attribute and pickle raises `PicklingError: ... it's not the same object as NoWires.coverage_pool._init_cov_pool`. The bug was latent on Windows through v1.5.4 because `should_use_multiprocessing()` returned False on most installs; v1.5.5's `pythonw.exe` detection made the gate succeed and exposed it. Fixed in v1.5.6 — see `tests/test_coverage_executor_reload_pickle.py` for the regression guard.
- When the multiprocessing branch raises, the fallback path calls `feedback.pushWarning("Multiprocessing unavailable ({}: {}), ...".format(type(exc).__name__, exc))` so the exception type and message surface in the QGIS Processing log panel. Earlier versions only logged via Python `logger.warning` and then `feedback.pushInfo("Multiprocessing unavailable, ...")` with no exception details; on GUI-subsystem QGIS builds (Windows `pythonw.exe`-bundled, some macOS configurations) the `logger.warning` `StreamHandler` can have `stream=None` and silently drop the diagnostic, leaving the user with an opaque "unavailable" message and no trail back to the underlying cause.

Raster positioning details:

- coverage task coordinates are generated at raster cell centers rather than raster edges
- the GeoTIFF writer uses the requested envelope as pixel bounds, so center-based sampling keeps the displayed heatmap aligned with the map extent
- this avoids the half-cell visual offset that can otherwise appear when sampling and georeferencing disagree

### Coverage Helper Split

The coverage support code is split by responsibility:

- `coverage/compute.py`
  Hosts the shared propagation-side helper used by coverage calculations
- `coverage/palette.py`
  Heatmap stop definitions
- `coverage/engine.py`
  Owns the grid walk, raster assembly, multiprocessing decisions, and integration logic
- `coverage/analysis_params.py`
  Coverage algorithm parameter registration
- `coverage/params.py`
  Coverage parameter definitions and defaults
- `coverage/pool.py`
  Coverage multiprocessing pool and shared-memory management
- `coverage/tasks.py`
  Per-pixel coverage task definitions
- `coverage/summary.py`
  Raster-derived usable-distance metrics
- `coverage/legend.py`
  Coverage legend support in QGIS; `show_coverage_legend()` constructs a
  `QFrame`, which **must** run on the main thread. With ALLOW_THREADING
  enabled (Coverage / Batch / Comparison), the algorithm stashes the
  legend's `rx_sens` during `processAlgorithm` and shows it in
  `postProcessAlgorithm` (main-thread-guaranteed by the Processing
  framework).
- `coverage/opacity.py`
  Live opacity adjustment dialog
- `coverage/reporting.py`
  Coverage report output helpers
- `coverage/dem_validate.py`
  Small helper that warns when the downloaded DEM doesn't fully cover the
  requested analysis bounds. Split out so `algorithm/coverage.py` stays
  within the 300-line cap.
- `report/pdf.py`
  Qt-based PDF report writer (`QTextDocument` + `QPrinter`) used by Coverage
  Analysis when `OUTPUT_REPORT_PDF` is set.

Important constants:

- `_get_max_workers()` returns `min(os.cpu_count() or 1, 16)` with lazy env-var lookup (capped at 16 workers via `NOWIRES_MAX_WORKERS`)
- `NOWIRES_PYTHON_EXE` env var (optional) explicitly points the spawn pool at a specific Python interpreter on macOS or Windows, bypassing auto-detection
- Dynamic chunk size via `_dynamic_chunk_size()`
- `_MIN_COVERAGE_DISTANCE_M = 1.0`
- `METERS_PER_DEGREE_LAT = 111320.0`
- `COVERAGE_NODATA = -9999.0` — NoData sentinel for coverage rasters. Chosen because GDAL Float32 NoData requires a finite value (NaN is not universally supported). -9999 is well outside both valid path-loss range (0–400 dB) and received-power range (≈-120 to +80 dBm).

### Raster NoData Convention

Coverage rasters use `COVERAGE_NODATA = -9999.0` as the missing-data sentinel. This value is outside the range of physically meaningful dB-loss and dBm values, so it cannot be confused with valid data. Programs consuming the raster programmatically should treat this value as missing, or use GDAL's NoData mask to filter it before arithmetic operations. NaN is not used because many GIS formats and GDAL drivers do not reliably round-trip NaN NoData values for Float32 rasters.

Internal functions that operate on in-memory grids (e.g., `compute_delta_summary`, `summarize_coverage_grid`) normalize `-9999.0` values to `NaN` at function entry, so that reload-then-compare paths produce correct results.

### Near-Transmitter Coverage Cells

The coverage engine now allows near-TX cells to be computed instead of leaving a transparent inner hole.

Implementation note:

- the engine avoids a true zero-distance ITM path by forcing a minimum modeled distance of `1.0 m`

### DEM Row Orientation

`elevation.py` treats GDAL row `0` as the north edge of the raster.

Implementation detail:

- direct DEM sampling and line sampling convert latitude to row index from `max_lat` downward
- this keeps terrain profiles, coverage terrain paths, and other DEM-derived outputs north-up instead of vertically mirrored

### Coverage Styling

The coverage raster uses:

- a `QgsColorRampShader` with `Discrete` color ramp type
- palette stops from `coverage/palette.py`
- a ceiling entry at `+100 dBm` (same color as Very Strong) so the `Discrete` shader covers all values up to +100 dBm
- layer opacity driven by a custom Processing slider wrapper
- a live plugin menu action for post-run coverage opacity adjustment

Signal level stops (Discrete mode — each entry is the upper boundary of its range):

| Range (dBm) | Label | Color | Alpha |
|---|---|---|---|
| > +100 | outside ramp | — | 0 (transparent) |
| -30 to +100 | Very Strong | dark green | 220 |
| -60 to -30 | Excellent | green | 210 |
| -75 to -60 | Good | light green | 200 |
| -85 to -75 | Fair | yellow-green | 195 |
| -95 to -85 | Marginal | yellow-orange | 190 |
| -105 to -95 | Weak | orange | 185 |
| -120 to -105 | No service (visible band) | dark red | 0 |
| ≤ -120 | No service (transparent) | dark red | 0 |

The "No service" stops at and below -120 dBm have alpha=0 by design so that cells with no usable signal reveal the base map.

The +100 dBm ceiling entry ensures that values above -30 dBm (including strong near-TX signals) are rendered with the Very Strong color instead of appearing transparent. In `QgsColorRampShader.Discrete` mode, values above the highest user-visible stop have no assigned color unless a ceiling entry extends the range.

The visual layer opacity is controlled independently from the per-stop alpha values in the heatmap palette.

Implementation detail:

- the coverage workflow applies opacity to both the `QgsRasterLayer` and its active raster renderer so the styled heatmap responds correctly to initial transparency and live slider updates in QGIS 4

### Benchmark Support

The repository includes `benchmarks/coverage_runtime.py`, a deterministic synthetic benchmark that exercises the real `compute_coverage()` path over named reference cases (`small`, `medium`, and `large`).

This benchmark is intended for local performance comparison and regression spotting; it is not a replacement for full in-QGIS validation.

### Coverage Summary

`coverage/summary.py` derives:

- usable cell count
- minimum usable distance
- maximum usable distance
- average usable distance

These metrics are based on raster cells at or above `RX sensitivity`.

## Coverage Comparison

### Purpose

`algorithm/coverage_comparison.py` runs two coverage configurations side-by-side and produces a delta raster showing the path-loss difference (Panel A minus Panel B) in dB.

### Comparison Flow

1. Read shared DEM and TX point from Panel A.
2. Run Panel A coverage with Panel A parameters.
3. Run Panel B coverage with Panel B parameters (same DEM, potentially different frequency, power, heights, etc.).
4. Compute a pixel-wise delta raster: `delta = loss_A - loss_B` (positive values mean Panel A has higher loss).
5. Apply diverging red–blue symbology to the delta raster.
6. Add layers and write optional reports.

### Comparison Parameters

All coverage parameters are available for each panel, plus:
- Panel A and Panel B have independent radio and antenna settings.
- A shared TX point and DEM are used for both panels.

### Comparison Outputs

- Delta raster (Panel A – Panel B path loss in dB)
- Dual-panel statistics report (CSV/JSON/HTML)
- Individual panel rasters are not loaded; only the delta and summary are shown

## Batch P2P Analysis

### Purpose

`algorithm/batch.py` computes multiple P2P links in one run, supporting one-to-many (single TX, multiple RX) and many-to-one (single RX, multiple TX) modes.

### Batch Flow

1. Read the fixed endpoint (TX or RX) and the set of opposite endpoints.
2. Download or reuse DEM covering all link paths.
3. Compute ITM path loss and link budget for each link.
4. Rank results by link margin (descending).
5. Write a combined results vector layer and optional CSV/JSON report.

### Batch Parameters

- Mode: one-to-many or many-to-one
- Fixed endpoint point
- Set of opposite-end points (vector layer)
- Standard P2P radio parameters (frequency, heights, climate, variability, power, gains, etc.)
- Optional antenna and clutter settings
- Output format selection

### Batch Outputs

- Combined vector layer with all link results
- Ranked link table (by margin)
- Optional CSV and JSON reports

## 3D Scene Support

`three_d.py` tracks the latest relevant NoWires output layers in project settings under the `NoWires` scope:

- `last_coverage_layer_id`
- `last_dem_layer_id`

Current behavior:

- coverage workflows update these tracked layer ids when they create 3D-relevant outputs
- Linux and macOS can request a plugin-opened 3D canvas through `iface.createNewMapCanvas3D(...)`
- Windows does not use that API path from the plugin because it caused native crashes during testing; the plugin shows a warning and defers to QGIS's native `View -> 3D Map Views -> New 3D Map View` workflow instead

## Parameter Reference

### Polarization

Values:

- `Horizontal`
- `Vertical`

Current default in both P2P and coverage:

- `Vertical`

### Climate Zones

Values:

- Equatorial
- Continental Subtropical
- Maritime Subtropical
- Desert
- Continental Temperate
- Maritime Temperate (land)
- Maritime Temperate (sea)

### Time / Location / Situation Percentages

These are ITM variability inputs.

Current defaults:

- `50.0`
- valid range enforced in the UI: `0.01` to `99.99`

### `N0`

Surface refractivity in N-units.

Default:

- `301.0`

In P2P and Batch, a non-Custom Earth-radius-factor preset overrides this field
via the `K_FACTOR_PRESET_N0` coupling table (see *Earth Radius Factor
Handling*), unless the **Decouple N0 from k-factor preset** checkbox is enabled
or the Custom preset is selected. Coverage uses the entered `N0` directly (no
preset).

### `epsilon`

Earth permittivity.

Default:

- `15.0`

### `sigma`

Earth conductivity in S/m.

Default:

- `0.005`

### RX Sensitivity

Used both as:

- a link-budget threshold in P2P
- a usable-cell threshold in coverage summary calculations

### Clutter Percentile (`CLUTTER_PERCENTILE`)

Location percentile for P.2108-1 §3.2 statistical clutter loss and P.2109-2 building entry loss.

- Range: `0.01` to `99.99`
- Default: `50.0`
- Lower percentile → lower loss (loss not exceeded for that percentage of locations)
- Same knob controls both §3.2 and BEL

### Street Width (`STREET_WIDTH_M`)

Street width parameter for P.2108-1 §3.1 height-gain terminal correction.

- Range: `5` to `100` m
- Default: `27.0` (P.2108-1 default)
- Only used in advanced clutter mode

### BEL Enabled (`BEL_ENABLED`)

Boolean toggle for P.2109-2 building entry loss.

- Default: `False`
- When enabled, building entry loss is computed for the RX terminal and added to the path budget
- TX terminal BEL is always 0.0 (outdoor transmitter assumption)
- Available in P2P, coverage, batch, and comparison workflows

### BEL Building Type (`BEL_BUILDING_TYPE`)

Building type for P.2109-2 building entry loss.

- Options: `Traditional` / `Thermally-efficient`
- Default: `Traditional`
- Thermally-efficient buildings have substantially higher BEL at most frequencies

### BEL Elevation Angle (`BEL_ELEVATION_ANGLE`)

Elevation angle of the path at the building façade (degrees above horizontal) for P.2109-2.

- Range: `0.0` to `90.0`°
- Default: `0.0` (horizontal incidence)
- Higher elevation angles increase BEL at 0.212 dB per degree

## Testing Strategy

The repository includes a fast `pytest` suite designed to run outside QGIS.

Test coverage includes:

- source-based regression checks for Processing contracts
- unit tests for pure Python helpers
- P.2108-1 §3.1 height-gain terminal correction (14 tests in `tests/test_p2108_height_gain.py`)
- P.2108-1 §3.2 statistical clutter loss (14 tests in `tests/test_p2108_terrestrial_stat.py`)
- P.2109-2 building entry loss (10 tests in `tests/test_p2109_bel.py`)
- P.2108/P.2109 shared inverse-normal helpers and sign-convention guards (24 tests in `tests/test_p2108_common.py`)
- coverage-engine behavior checks
- benchmark and module-split regressions
- 3D support contract checks
- source-based checks for QGIS 4 / Qt 6 API usage

GitHub Actions runs `pytest -q` for pushes and pull requests.

## Compatibility Notes

### QGIS Version

- target platform: QGIS 4.x
- metadata currently advertises `qgisMinimumVersion=4.0`
- Qt target: Qt 6 / PyQt 6 as provided by QGIS 4; Qt 5 compatibility shims are intentionally not supported

### Runtime Assumptions

- many tests run without QGIS installed
- live Processing widget behavior still depends on actual QGIS runtime
- manual QGIS validation is still important for UI-heavy changes

### Processing Parameter Compatibility

When changing parameter keys or types, compatibility with stored Processing models and scripts must be considered explicitly.

The `K_FACTOR` / `K_FACTOR_PRESET` / `DECOUPLE_N0` handling in `algorithm/p2p.py` is an example of evolving behavior while preserving an escape hatch: the preset now drives `N0` by default (a deliberate v2.0.0 change), while the Decouple checkbox and the Custom preset keep the legacy `N0`-independent workflow available.

Output parameters for algorithms use `QgsProcessingParameterFileDestination` rather than `RasterDestination` or `VectorDestination`. This avoids a double-loading conflict: the `*Destination` types tell QGIS Processing to auto-load the output layer, but the algorithms also queue layers via `addLayerToLoadOnCompletion` with custom styling. Using `FileDestination` means only the manually-queued load with proper styling occurs.

### Layer Loading in processAlgorithm

All three algorithms use a shared `_queue_layer_for_loading()` helper that adds layers to the processing context's temporary layer store and registers them for deferred loading via `addLayerToLoadOnCompletion`. This avoids calling `QgsProject.instance().addMapLayer()` from inside `processAlgorithm`, which mutates the project from a worker thread and causes a Windows access violation crash.

A `postProcessAlgorithm` override in `base_algorithm.py` reorders raster layers to the bottom of the layer tree and writes project-level metadata (`last_dem_layer_id`, `last_coverage_layer_id`) via `QgsProject.instance().writeEntry`. Moving these writes out of `processAlgorithm` respects the QGIS processing design contract that `processAlgorithm` should be side-effect-free with respect to the project instance.

## Known Limitations

- Coverage performance degrades as grid size and analysis distance grow.
- Plugin-launched 3D canvas creation is disabled on Windows because it caused native QGIS crashes in this workflow.
- Batch P2P analysis currently uses the same DEM for all links within a run; very spread-out point sets may require padding the DEM extent.
- Coverage comparison requires both panels to share the same DEM and grid extent.
- DEM access depends on external network availability.
- The repository test suite does not substitute for in-QGIS manual validation.
- P.2108-1 §3.2 is a combined urban+suburban statistic; it should not be applied to open or rural categories (the plugin enforces this by only invoking §3.2 for suburban and urban categories).
- P.2109-2 BEL elevation angle in coverage analysis is a fixed user-set value per run; per-pixel elevation computation is out of scope for the current version.

## ITM Propagation Edge Cases

The bundled ITM implementation (`itm/propagation.py`) handles several edge cases that can arise with extreme parameter combinations:

### Smooth Earth Diffraction (NC1 Fix)

When `K = 0.017778 × C₀ × f^(-⅓) / |Z_g|` exceeds 1.607, the term `B₀ = 1.607 − K` goes negative. This occurs at low frequencies (≤ 20 MHz) with vertical polarization over high-conductivity ground (small `|Z_g|`). Previously this caused `ValueError` from `log10(≤0)`. The fix:

- `height_function(x__km, K)` returns `200.0` (a large finite dB loss) when `x__km ≤ 0` or `K ≤ 0`
- `smooth_earth_diffraction` clamps `B₀[i]` to a minimum of `1e-12` when `K > 1.607`
- When `x__km[0] ≤ 0`, `G_x__db` returns a large loss value instead of calling `log10`

This preserves monotonicity and produces a physically reasonable high-loss result instead of crashing.

### Coverage Engine Robustness (NC2 / NI1 / NI2 Fixes)

- Per-task exception handling in `_itm_worker_batch` prevents one bad pixel from killing an entire chunk of coverage tasks
- The outer `except` clause in `execute_coverage_tasks` catches all `Exception` types, not just specific ones, ensuring fallback to sequential mode for any worker failure
- Cancellation is **not** propagated to in-flight workers via any cross-process signal — `_itm_worker_batch` takes a plain batch argument (no `cancel_event`) and the main thread cancels by breaking out of `pool.map` between batches. In-flight batches finish naturally (~320 ms worst case at default chunk size). Two earlier attempts on v1.5.5 (plain `multiprocessing.Event()`, then `Manager().Event()`) both failed on macOS QGIS — the spawn-mode pickle path raises for the former and the Manager subprocess dies with `EOFError` for the latter.
- The initializer and worker-batch callable are resolved by a function-local `from .coverage_pool import _init_cov_pool, _itm_worker_batch` inside `execute_coverage_tasks` (fixed in v1.5.6). A module-scope import would freeze the references at first load and break `pickle`'s identity check the next time `NoWires.coverage_pool` was reloaded — see the "Multiprocessing in QGIS" section above for the full failure mode and `tests/test_coverage_executor_reload_pickle.py` for the regression guard.
- `_final_cov_pool()` is registered with `atexit` on each worker process for shared-memory cleanup; per-worker handles are also cleaned up by the OS on process exit.

## Public Repository Files

For GitHub upload and maintenance, the repository also includes:

- [README.md](README.md)
- [USERS-GUIDE.md](USERS-GUIDE.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CHANGELOG.md](CHANGELOG.md)
- [NOTICE.md](NOTICE.md)
- [LICENSE](LICENSE)

## External References

- QGIS download page: https://qgis.org/download/
- QGIS installation guide: https://version.qgis.org/resources/installation-guide/
- QGIS plugin repository guidance: https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/plugins/releasing.html
