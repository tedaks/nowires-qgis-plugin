# NoWires — QGIS Plugin

Radio propagation analysis and terrain tools powered by NTIA's Irregular Terrain Model (ITM) with Copernicus GLO-30 DEM.

## Status

This repository contains the QGIS 4 plugin source for **NoWires**.

## Features

### Radio Propagation
- **Point-to-Point Analysis**: Place TX and RX points on the map. Computes ITM path loss, terrain profile with Fresnel zone analysis, and generates a detailed link budget report. Creates vector layers showing the link path and Fresnel zone geometry.
- **Coverage Analysis**: Place a transmitter, set a max analysis distance and grid resolution, then generate a heatmap raster showing received signal strength (dBm) plus range statistics derived from cells above sensitivity.

### Terrain Analysis
- **Contour Lines**: Generate contour lines with rule-based symbology (index contours with labels) from Copernicus GLO-30 DEM. Adjustable interval (1–5000 m or ft), four smoothing levels, and custom colour.
- **Hillshade Overlay**: Optional hillshade elevation layer rendered from the raw DEM with Dodge blending.

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
- `itm/`: bundled ITM implementation
- `tests/`: regression and unit tests
- `metadata.txt`: QGIS plugin metadata

## Usage

Open the **Processing Toolbox** (`Ctrl+Alt+T`) and navigate to **NoWires**:

1. **Point-to-Point Analysis**: Select TX and RX points, configure frequency, antenna heights, and link parameters. Click Run.
2. **Coverage Analysis**: Select a TX point, set max analysis distance and grid resolution. Click Run to generate a signal-strength heatmap raster and coverage summary.
3. **Contour Lines**: Draw an extent, set contour interval and smoothing. Generates contour lines and optional hillshade.

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
3. Copy the `NoWires` folder into your QGIS plugins directory for manual testing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution notes.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for notable project changes.

## License

GNU General Public License v3 or later.
Third-party notices and upstream attribution details are documented in [NOTICE.md](NOTICE.md).
