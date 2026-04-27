# NoWires Technical Documentation

## Purpose

This document describes the NoWires plugin from a technical and implementation perspective. It is intended for developers, maintainers, and advanced users who need more detail than the user guide provides.

For installation and routine use, see [USERS-GUIDE.md](USERS-GUIDE.md).

## Scope

NoWires is a QGIS 4 plugin that combines:

- point-to-point radio propagation analysis
- area coverage heatmap analysis
- contour line generation
- DEM download, caching, clipping, and derived overlay support

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

- [algorithm_p2p.py](algorithm_p2p.py)
  Point-to-point analysis
- [algorithm_coverage.py](algorithm_coverage.py)
  Coverage heatmap analysis
- [algorithm_contour.py](algorithm_contour.py)
  Contour and hillshade/elevation overlay workflow

### Supporting Modules

- [radio.py](radio.py)
  ITM bridge, Fresnel analysis, signal-level definitions
- [coverage_engine.py](coverage_engine.py)
  Coverage raster computation
- [coverage_compute.py](coverage_compute.py)
  Shared coverage propagation helpers
- [coverage_colors.py](coverage_colors.py)
  Coverage color-application helpers
- [coverage_summary.py](coverage_summary.py)
  Raster-derived usable-distance metrics
- [coverage_palette.py](coverage_palette.py)
  Heatmap stop definitions
- [coverage_legend.py](coverage_legend.py)
  Coverage legend support in QGIS
- [coverage_opacity.py](coverage_opacity.py)
  Live opacity adjustment dialog for the latest coverage layer
- [reliability.py](reliability.py)
  Formal-or-fallback availability and reliability helpers
- [report_export.py](report_export.py)
  Shared CSV, JSON, and HTML report writers
- [report_payloads.py](report_payloads.py)
  Pure-Python payload builders and P2P marker helpers
- [elevation.py](elevation.py)
  DEM sampling, terrain profiles, geographic helpers
- [dem_downloader.py](dem_downloader.py)
  Copernicus GLO-30 download, cache, merge, clip
- [antenna.py](antenna.py)
  Directional antenna gain adjustment, presets, pattern files, and vertical downtilt
- [clutter.py](clutter.py)
  Terminal clutter correction helpers
- [worldcover_downloader.py](worldcover_downloader.py)
  ESA WorldCover 2020 v100 tile download, caching, and clip/merge
- [overlay_raster.py](overlay_raster.py)
  Overlay raster sizing helpers
- [three_d.py](three_d.py)
  3D layer tracking and scene-opening helpers

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
- `contour_lines`

The older `coverage radius sweep` workflow remains on disk in `algorithm_coverage_radius.py` but is no longer registered for normal plugin use.

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

In addition to Processing algorithms, the plugin exposes two post-run helper actions from the `NoWires` menu:

- `Coverage Opacity`
  Opens a non-modal slider dialog for the latest tracked coverage layer
- `Open 3D View`
  Opens a QGIS 3D scene from the latest tracked NoWires DEM, coverage, and contour layers when supported by the runtime platform

## Point-to-Point Analysis

### Purpose

`algorithm_p2p.py` computes a single ITM link between a transmitter and receiver and then performs Fresnel-zone and earth-curvature analysis on the sampled terrain profile.

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

Point-to-point analysis now produces:

- profile line output
- Fresnel zone output
- TX/RX marker output
- optional `CSV`, `JSON`, and `HTML` reports

Point-to-point reports carry reliability and clutter fields:

- `availability_method`
- `availability_estimate_pct`
- `fade_margin_class`
- `reliability_summary`
- `clutter_source`
- `clutter_tx_db`
- `clutter_rx_db`
- `total_path_loss_db`

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
- Earth radius factor preset

#### Advanced inputs

- custom Earth radius factor (`K_FACTOR`)
- `N0`
- `epsilon`
- `sigma`
- antenna preset, azimuth, beamwidth, front-to-back ratio, downtilt, and optional pattern CSV files
- clutter model (Off / Simple clutter correction)
- clutter raster path (optional; auto-downloads WorldCover when clutter is enabled and left blank)
- TX clutter override
- RX clutter override

### Earth Radius Factor Handling

Visible presets:

- `0.67 - Sub-refractive`
- `1.00 - Geometric`
- `1.33 - Standard atmosphere`
- `2.00 - Super-refractive`
- `4.00 - Strong super-refractive`

Default:

- `1.33 - Standard atmosphere`

Backward compatibility:

- the older numeric `K_FACTOR` parameter is still present as an advanced field
- if an older Processing model supplies `K_FACTOR` without the new preset parameter, the numeric value is still honored

This preserves compatibility with legacy workflows while giving interactive users clearer defaults.

### Why `k` Only Affects P2P

In the current codebase, Earth radius factor is used in the Fresnel and earth-bulge visualization path for point-to-point analysis. Coverage analysis does not currently expose `k` as a coverage parameter.

## Coverage Analysis

### Purpose

`algorithm_coverage.py` produces a received-signal raster and derives usable-range metrics from that raster.

### Coverage Flow

1. Read the transmitter point and user inputs.
2. Treat `Max analysis distance (km)` as the outer computation envelope.
3. Download and prepare a DEM covering that envelope.
4. Build a dense elevation grid.
5. Call `compute_coverage()` in [coverage_engine.py](coverage_engine.py).
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
- `clutter_tx_db`
- `clutter_rx_db`
- `itm_loss_db` (grid-wide mean over valid pixels)
- `total_path_loss_db` (grid-wide mean over valid pixels)

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
- clutter model (Off / Simple clutter correction)
- clutter raster path (optional; auto-downloads WorldCover when clutter is enabled and left blank)
- TX clutter override
- RX clutter override

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

`coverage_engine.py` is responsible for per-pixel propagation computation.

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

`clutter.py` implements the optional terminal correction layer. It keeps ITM unchanged, samples a WorldCover-compatible raster at terminal locations, maps raw classes to propagation categories, and adds terminal losses after ITM.

Key helpers:

- `compute_terminal_clutter_losses()`: resolves TX and RX clutter categories (from override, raster sample, or `open` fallback) and returns a `TerminalClutterLosses` dataclass with `tx_loss_db`, `rx_loss_db`, `total_loss_db`, and a `source` label.
- `clutter_source_label()`: builds a user-visible source string for reports (e.g. `"override,/tmp/worldcover.vrt"` or `"fallback_open"`).
- `clutter_override_value()`: converts a Processing parameter index or category string into a category name or `None`.
- `LandCoverGrid.from_raster()`: loads a land-cover GeoTIFF into a `LandCoverGrid` with geographic bounds and no-data handling.
- `LandCoverGrid.sample_category()`: samples the grid at a given lat/lon and returns a clutter category string.
- `ensure_clutter_grid_for_area()`: auto-downloads WorldCover tiles when clutter is enabled and no raster is supplied.

Clutter categories and loss table:

| Category | Loss (dB) |
|---|---|
| open | 0.0 |
| rural | 2.0 |
| vegetation | 6.0 |
| suburban | 8.0 |
| urban | 10.0 |

WorldCover class-to-category mapping (`worldcover_class_to_clutter_category`):

| WorldCover class | Category |
|---|---|
| 10, 95, 100 | vegetation |
| 20, 30, 40 | rural |
| 50 | urban |
| 60, 70, 80, 90 | open |

### Clutter Reporting

Both P2P and coverage reports expose clutter loss breakdown:

- `clutter_source`: a descriptive label produced by `clutter_source_label()` rather than a raw file path.
- `clutter_tx_db`: TX terminal clutter loss (dB).
- `clutter_rx_db`: RX terminal clutter loss (dB).
- `total_path_loss_db`: `itm_loss_db + clutter_tx_db + clutter_rx_db`.

For coverage reports, `itm_loss_db` and `total_path_loss_db` are grid-wide means over valid pixels, `clutter_tx_db` is the TX terminal loss at the transmitter location, and `clutter_rx_db` is derived as `clutter_total_mean - clutter_tx_db`.

For P2P reports, clutter losses are computed per terminal using `compute_terminal_clutter_losses()` and included directly.

### Multiprocessing Note

- Windows defaults to single-process mode to avoid spawning extra QGIS instances
- non-Windows runtimes may use multiprocessing with shared memory

Raster positioning details:

- coverage task coordinates are generated at raster cell centers rather than raster edges
- the GeoTIFF writer uses the requested envelope as pixel bounds, so center-based sampling keeps the displayed heatmap aligned with the map extent
- this avoids the half-cell visual offset that can otherwise appear when sampling and georeferencing disagree

### Coverage Helper Split

The coverage support code is now split by responsibility:

- `coverage_compute.py`
  Hosts the shared propagation-side helper used by coverage calculations
- `coverage_colors.py`
  Hosts coverage color-application helpers
- `coverage_engine.py`
  Owns the grid walk, raster assembly, multiprocessing decisions, and integration logic

Important constants:

- `_MAX_WORKERS = os.cpu_count() or 1` (auto-detected)
- Dynamic chunk size via `_dynamic_chunk_size()`
- `_MIN_COVERAGE_DISTANCE_M = 1.0`
- `METERS_PER_DEGREE_LAT = 111320.0`

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

- an interpolated `QgsColorRampShader`
- palette stops from `coverage_palette.py`
- layer opacity driven by a custom Processing slider wrapper
- a live plugin menu action for post-run coverage opacity adjustment

The visual layer opacity is controlled independently from the per-stop alpha values in the heatmap palette.

Implementation detail:

- the coverage workflow applies opacity to both the `QgsRasterLayer` and its active raster renderer so the styled heatmap responds correctly to initial transparency and live slider updates in QGIS 4

### Benchmark Support

The repository includes `benchmarks/coverage_runtime.py`, a deterministic synthetic benchmark that exercises the real `compute_coverage()` path over named reference cases (`small`, `medium`, and `large`).

This benchmark is intended for local performance comparison and regression spotting; it is not a replacement for full in-QGIS validation.

### Coverage Summary

`coverage_summary.py` derives:

- usable cell count
- minimum usable distance
- maximum usable distance
- average usable distance

These metrics are based on raster cells at or above `RX sensitivity`.

## Contour Lines

### Purpose

`algorithm_contour.py` generates contour lines and an optional elevation overlay from downloaded Copernicus DEM data.

### Contour Inputs

- area of interest extent
- interval
- units
- smoothing level
- line color
- optional elevation overlay
- optional proxy authentication

### Contour Constraints

- contour interval range: `1` to `5000`
- area-of-interest maximum extent: `5.0°` width or height

## 3D Scene Support

`three_d.py` tracks the latest relevant NoWires output layers in project settings under the `NoWires` scope:

- `last_coverage_layer_id`
- `last_dem_layer_id`
- `last_contour_layer_id`

Current behavior:

- coverage and contour workflows update these tracked layer ids when they create 3D-relevant outputs
- contour layers are configured for terrain-aware elevation when used in 3D
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

## Testing Strategy

The repository includes a fast `pytest` suite designed to run outside QGIS.

Test coverage includes:

- source-based regression checks for Processing contracts
- unit tests for pure Python helpers
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

The `K_FACTOR` / `K_FACTOR_PRESET` handling in `algorithm_p2p.py` is an example of preserving legacy behavior while evolving the UI.

Output parameters for algorithms use `QgsProcessingParameterFileDestination` rather than `RasterDestination` or `VectorDestination`. This avoids a double-loading conflict: the `*Destination` types tell QGIS Processing to auto-load the output layer, but the algorithms also queue layers via `addLayerToLoadOnCompletion` with custom styling. Using `FileDestination` means only the manually-queued load with proper styling occurs.

### Layer Loading in processAlgorithm

All three algorithms use a shared `_queue_layer_for_loading()` helper that adds layers to the processing context's temporary layer store and registers them for deferred loading via `addLayerToLoadOnCompletion`. This avoids calling `QgsProject.instance().addMapLayer()` from inside `processAlgorithm`, which mutates the project from a worker thread and causes a Windows access violation crash.

A `postProcessAlgorithm` override in the coverage and contour algorithms reorders raster layers to the bottom of the layer tree after QGIS finishes loading them, so DEM and hillshade overlays render beneath vector and coverage layers.

## Known Limitations

- Coverage performance degrades as grid size and analysis distance grow.
- Coverage multiprocessing is intentionally disabled on Windows.
- Plugin-launched 3D canvas creation is disabled on Windows because it caused native QGIS crashes in this workflow.
- The coverage radius-sweep implementation has been removed.
- DEM access depends on external network availability.
- The repository test suite does not substitute for in-QGIS manual validation.

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
