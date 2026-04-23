# NoWires — QGIS Plugin

Radio propagation analysis and terrain tools powered by NTIA's Irregular Terrain Model (ITM) with Copernicus GLO-30 DEM.

## Status

This repository contains the QGIS 4 plugin source for **NoWires**.

## Features

### Radio Propagation
- **Point-to-Point Analysis**: Place TX and RX points on the map. Computes ITM path loss, terrain profile with Fresnel zone analysis, generates CSV/JSON/HTML reports, and creates vector layers for the link path, Fresnel geometry, and TX/RX markers.
- **Coverage Analysis**: Place a transmitter, set a max analysis distance and grid resolution, then generate a heatmap raster showing received signal strength (dBm) plus range statistics derived from cells above sensitivity, with optional CSV/JSON/HTML report export. Coverage cells are sampled and georeferenced at cell centers so the heatmap lines up with the terrain and requested map extent.
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

- QGIS 4.0 or later
- Internet connection (for DEM tile downloads)
- GDAL (bundled with QGIS)
- numpy (bundled with QGIS)

No additional Python packages need to be installed. The ITM library ([tedaks/pyitm](https://github.com/tedaks/pyitm)) is bundled with this plugin.
This plugin also adapts code from [tedaks/nowires](https://github.com/tedaks/nowires) and [tedaks/ContourLines](https://github.com/tedaks/ContourLines); see [NOTICE.md](NOTICE.md) for third-party attribution and license details.

## Installation

1. Copy the `NoWires` folder to your QGIS user plugins directory:
   - **Linux/macOS:** `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/`
   - **Windows:** `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\`

2. Restart QGIS and enable the plugin in **Plugins → Manage and Install Plugins**.

## Repository Layout

- `algorithm_p2p.py`: point-to-point ITM analysis
- `algorithm_coverage.py`: coverage heatmap analysis
- `algorithm_contour.py`: contour line generation
- `coverage_engine.py`: coverage raster computation engine
- `coverage_compute.py`: shared coverage propagation helpers
- `coverage_colors.py`: coverage color-application helpers
- `coverage_opacity.py`: live coverage opacity dialog
- `reliability.py`: formal-or-fallback availability and reliability helpers
- `report_export.py`: shared CSV/JSON/HTML report writers
- `report_payloads.py`: pure-Python report payload and marker helpers
- `three_d.py`: 3D layer tracking and scene helpers
- `benchmarks/coverage_runtime.py`: synthetic coverage runtime benchmark
- `itm/`: bundled ITM implementation
- `tests/`: regression and unit tests
- `metadata.txt`: QGIS plugin metadata

## Usage

Open the **Processing Toolbox** (`Ctrl+Alt+T`) and navigate to **NoWires**:

1. **Point-to-Point Analysis**: Select TX and RX points, configure frequency, antenna heights, and link parameters. Click Run to generate the link outputs, TX/RX markers, and any requested reports.
2. **Coverage Analysis**: Select a TX point, set max analysis distance and grid resolution. Click Run to generate a signal-strength heatmap raster, coverage summary, and any requested reports.
3. **Contour Lines**: Draw an extent, set contour interval and smoothing. Generates contour lines and optional hillshade.
4. **Coverage Opacity**: After running coverage, open the menu action to adjust the latest coverage raster opacity live.
5. **Open 3D View**: After running coverage or contours, open a tracked 3D scene from the plugin menu on Linux/macOS. On Windows, NoWires now points you to the native QGIS 3D view and tells you to use the NoWires DEM as terrain.

## Data Source

Elevation data: **Copernicus GLO-30 Public DEM** hosted on AWS Open Data.
- Registry: https://registry.opendata.aws/copernicus-dem/
- Copernicus DEM © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

## Credits

- Radio propagation engine: [tedaks/pyitm](https://github.com/tedaks/pyitm) — NTIA Irregular Terrain Model (bundled)
- Original web application: [tedaks/nowires](https://github.com/tedaks/nowires)
- Contour lines algorithm: [ContourLines](https://github.com/tedaks/ContourLines) by Daniel Hulshof Saint Martin
- gdal_calc utility: GDAL project (Chris Yesson, Even Rouault, Piers Titus van der Torren)

## Development

The test suite in this repository is designed to run outside QGIS for fast regression checks.

### Run tests

```bash
pytest -q
```

### Typical local workflow

1. Make changes in the plugin source.
2. Run `pytest -q`.
3. Optionally run `python3 benchmarks/coverage_runtime.py` to compare runtime against the reference synthetic cases.
4. Copy the `NoWires` folder into your QGIS plugins directory for manual testing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution notes.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for notable project changes.

## License

GNU General Public License v3 or later.
Third-party notices and upstream attribution details are documented in [NOTICE.md](NOTICE.md).
