# NoWires User's Guide

SPDX-License-Identifier: GPL-3.0-or-later

## Overview

NoWires is a QGIS 4 plugin for:

- point-to-point radio link analysis
- coverage heatmap analysis
- contour line generation from Copernicus GLO-30 DEM data

This guide is for end users. It focuses on installation, setup, and basic workflows. For implementation details and engineering reference material, see [Technical_Documentation.md](Technical_Documentation.md).

## Before You Start

You will need:

- a computer running Windows, Linux, or macOS
- permission to install QGIS and copy files into your QGIS profile
- an internet connection for downloading QGIS, the plugin, and DEM tiles

## Install QGIS 4

Use the official QGIS download page:

- Main download page: https://qgis.org/download/
- Installation guide: https://version.qgis.org/resources/installation-guide/

Always check the official QGIS page for the latest 4.x installer and platform-specific notes.

### Windows

Recommended path:

1. Go to `https://qgis.org/download/`.
2. Download a QGIS 4 Windows installer.
3. Run the installer.
4. Launch QGIS once to let it create your user profile.

### macOS

Recommended path:

1. Go to `https://qgis.org/download/`.
2. Download the official QGIS 4 macOS package.
3. Open the downloaded installer image and drag QGIS into `Applications`.
4. Launch QGIS once to let it create your user profile.

### Linux

Recommended path:

1. Go to `https://qgis.org/download/`.
2. Follow the instructions for your distribution.
3. Install QGIS 4.x using the recommended repository or package method for your platform.
4. Launch QGIS once to let it create your user profile.

## Download the Plugin from GitHub

Three download options are available:

### Option 1: Release ZIP (recommended)

1. Go to the [GitHub Releases](https://github.com/tedaks/nowires-qgis-plugin/releases) page.
2. Download the `NoWires-X.Y.Z.zip` file from the latest release.
3. The ZIP is a ready-to-install plugin bundle — no extraction or renaming needed.

### Option 2: Download Source ZIP

1. Open the GitHub repository page for NoWires.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the archive and rename the extracted folder to `NoWires`.

Important:

- The files `__init__.py` and `metadata.txt` must be directly inside the `NoWires` folder.

### Option 3: Clone with Git

```bash
git clone https://github.com/tedaks/nowires-qgis-plugin.git
```

If needed, rename the cloned folder to `NoWires` before installing it into QGIS.

## Install the Plugin into QGIS

### Recommended Method: Install from ZIP

1. Download the release ZIP (`NoWires-X.Y.Z.zip`) from [GitHub Releases](https://github.com/tedaks/nowires-qgis-plugin/releases).
2. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the downloaded ZIP file and click **Install Plugin**.
4. QGIS installs the plugin automatically and prompts you to enable it.

This method works on all platforms and avoids manual folder placement.

### Alternative Method: Manual Folder Copy

1. Start QGIS.
2. Open your active profile folder from QGIS.
   Typical places to look are:
   - `Settings` -> `User Profiles`
   - or another menu entry that opens the active profile folder directly
3. Inside the active profile folder, create `python/plugins` if it does not already exist.
4. Copy the `NoWires` folder into that `python/plugins` folder.

Result:

```text
<active-profile-folder>/python/plugins/NoWires
```

### Typical Profile Locations (for manual copy)

- Windows: `%APPDATA%\\QGIS\\QGIS4\\profiles\\default\\python\\plugins`
- Linux: `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins`
- macOS: use the active profile folder from inside QGIS, then go into `python/plugins`

## Enable the Plugin

1. Restart QGIS after copying the folder.
2. Open `Plugins` -> `Manage and Install Plugins`.
3. Find `NoWires`.
4. Enable it.

You should then see:

- a `NoWires` Processing provider
- menu entries for:
  - `Point-to-Point Analysis`
  - `Coverage Analysis`
  - `Contour Lines`
  - `Coverage Comparison`
  - `Batch P2P Analysis`
  - `Coverage Opacity`
  - `Clear DEM Cache`
  - `Preview Antenna Pattern`
  - `Open 3D View`

## Where to Find the Tools

Open the Processing Toolbox:

```text
Processing -> Toolbox
```

or use:

```text
Ctrl+Alt+T
```

Then find the `NoWires` provider.

## Basic Workflow: Point-to-Point Analysis

Use this tool when you want to evaluate a single radio link between a transmitter and a receiver.

### Inputs

Main inputs include:

- transmitter point
- receiver point
- TX and RX antenna heights
- frequency
- polarization
- climate zone
- time, location, and situation percentages
- TX power, antenna gains, cable loss
- RX sensitivity
- Earth radius factor preset

Advanced inputs include:

- custom Earth radius factor (`k`) for backward compatibility
- surface refractivity (`N0`)
- earth permittivity (`epsilon`)
- earth conductivity (`sigma`)
- antenna preset, azimuth, beamwidth, front-to-back ratio, downtilt, and optional pattern CSV files
- clutter model (Off / Simple clutter correction / Advanced clutter correction)
- clutter raster path (optional; auto-downloads WorldCover when enabled and left blank)
- TX and RX clutter overrides
- canopy/clutter height override (CCH_OVERRIDE) for advanced mode

### What It Produces

- ITM path loss result
- link budget values
- Fresnel zone analysis
- vector outputs for the path, Fresnel geometry, and TX/RX markers
- clutter loss breakdown (`clutter_tx_db`, `clutter_rx_db`, `total_path_loss_db`) when clutter correction is enabled
- canopy heights (`tx_cch_m`, `rx_cch_m`) when advanced clutter correction is enabled
- antenna gain adjustment in the link budget when a directional antenna preset is used
- optional `CSV`, `JSON`, and `HTML` reports
- optional profile chart with hover callouts, Fresnel toggle, and export

### Basic Steps

1. Open `Point-to-Point Analysis`.
2. Select a TX point and an RX point.
3. Enter antenna heights and frequency.
4. Leave defaults in place if you are unsure, especially for:
   - polarization
   - variability percentages
   - Earth radius factor preset
5. Run the algorithm.
6. Review the created layers and Processing log output.

### Optional Report Export

Point-to-point analysis can also write:

- `CSV`
- `JSON`
- `HTML`

These exports contain the link inputs, path summary, link-budget values, Fresnel status, and viability summary from the run.

### Reliability Output

P2P reports now also include:

- `fade_margin_class`
- `availability_method`
- `availability_estimate_pct` when the formal method is used
- `reliability_summary`

Interpretation:

- `formal_p530` means the plugin judged the case suitable for the formal availability path
- `fallback_margin` means the plugin used the margin-based fallback summary instead

### Profile Chart

Point-to-point analysis can produce an interactive profile chart showing:

- terrain profile with earth curvature
- Fresnel zone outline (first Fresnel zone)
- LOS line between TX and RX
- hover callouts for terrain elevation and Fresnel clearance
- toggle buttons for Fresnel zone, LOS, and profile line visibility
- chart export to PNG/SVG

### Good Defaults for New Users

- Polarization: `Vertical`
- Time / Location / Situation: `50 / 50 / 50`
- Earth radius factor preset: `1.33 - Standard atmosphere`

## Basic Workflow: Coverage Analysis

Use this tool when you want to estimate signal level over an area around a transmitter.

### Inputs

Main inputs include:

- transmitter point
- TX and RX antenna heights
- frequency
- max analysis distance
- grid size resolution
- overlay transparency
- polarization
- climate zone
- time, location, and situation percentages
- TX power, gains, cable loss
- RX sensitivity
- antenna azimuth and beamwidth
- antenna preset, front-to-back ratio, downtilt, and optional pattern CSV files
- clutter model (Off / Simple clutter correction / Advanced clutter correction)
- clutter raster path (optional; auto-downloads WorldCover when enabled and left blank)
- TX and RX clutter overrides
- canopy/clutter height override (CCH_OVERRIDE) for advanced mode

### Antenna Presets And Pattern Files

NoWires treats the numeric TX/RX gain as the peak antenna gain. The antenna preset adds a relative pattern adjustment: boresight is normally `0 dB`, while off-axis directions are reduced. `Omni` preserves the older behavior. `Sector 90`, `Sector 120`, and `Dish 20` provide common planning shapes with configurable azimuth, front-to-back ratio, and downtilt.

Optional pattern CSV files use two numeric columns:

```csv
angle_deg,gain_adjust_db
0,0
90,-12
180,-30
270,-12
360,0
```

Horizontal pattern angles wrap around 360 degrees. Vertical pattern angles are clamped to the file range.

### Clutter / Land-Cover Correction

NoWires offers three clutter modes:

- **Off** — no terminal clutter correction.
- **Simple clutter correction** — flat per-category losses (legacy behaviour, unchanged). When enabled, NoWires samples land cover at the TX and RX terminals, maps the raw class into `open`, `rural`, `vegetation`, `suburban`, or `urban`, and adds terminal excess loss after ITM:

```text
total_path_loss_db = itm_loss_db + clutter_tx_db + clutter_rx_db
```

The simple loss table is:

| Category | Loss (dB) |
|---|---|
| open | 0.0 |
| rural | 2.0 |
| vegetation | 6.0 |
| suburban | 8.0 |
| urban | 10.0 |

- **Advanced clutter correction** — ITU-R P.2108-1 §3.1 height-gain terminal correction for low-frequency (0.03–3 GHz) rural categories; P.2108-1 §3.2 statistical clutter loss for suburban/urban (0.5–67 GHz); saalos vegetation model for vegetation categories. Suburban and urban categories apply both §3.1 and §3.2 in the overlap band (0.5–3 GHz) and take the maximum. Loss increases with frequency for built categories, consistent with P.2108-1. When the antenna is at or above the canopy/clutter height, the model gates the loss to zero for that terminal. An optional canopy/clutter height override (CCH_OVERRIDE) parameter lets you specify the effective canopy height.
- **Building entry loss (BEL)** — ITU-R P.2109-2 building entry loss model. When enabled, adds indoor penetration loss at the receiver based on building type (Traditional or Thermally-efficient), elevation angle, and frequency. Applied to RX only (TX is assumed outdoor). Available under advanced clutter settings.

Use TX/RX overrides when the raster is unavailable or visibly wrong. Neither simple nor advanced clutter models sample clutter along the full path — they apply terminal corrections only.

When clutter is enabled and the land-cover raster field is left blank, NoWires automatically downloads the required ESA WorldCover 2020 tiles from the AWS open data bucket. Tiles are cached locally in a temporary directory for reuse. If the download fails, the correction falls back to `open` (0 dB) with a warning in the log.

#### Advanced Mode Runtime Cost

Advanced clutter mode applies ITU-R P.833-9 §2.1 Am for vegetation cells (a single multiply per pixel — essentially no overhead) and vectorized P.2108 for built-environment categories.

#### Advanced Clutter Parameters

When advanced clutter correction is enabled, additional parameters become available:

- **Clutter Percentile** (0.01–99.99, default 50.0): Location percentile for P.2108-1 §3.2 statistical clutter loss and P.2109-2 building entry loss. Lower percentile → lower loss (loss not exceeded for that percentage of locations). The same knob controls both §3.2 and BEL.
- **Street Width** (5–100 m, default 27): Street width parameter for P.2108-1 §3.1 height-gain terminal correction.
- **BEL Enabled** (boolean, default off): When enabled, P.2109-2 building entry loss is added to the RX terminal. TX terminal BEL is always 0.0 (outdoor transmitter).
- **BEL Building Type** (Traditional / Thermally-efficient, default Traditional): Building type for P.2109-2. Thermally-efficient buildings have substantially higher loss at most frequencies.
- **BEL Elevation Angle** (0–90°, default 0): Elevation angle of the path at the building façade. Higher angles increase BEL at 0.212 dB per degree. Default 0° corresponds to horizontal incidence.

#### P.2108 Model Dispatch

The advanced clutter mode automatically selects the correct ITU-R sub-model based on clutter category and frequency:

| Category | f < 0.5 GHz | 0.5–3 GHz | 3–67 GHz | > 67 GHz |
|---|---|---|---|---|
| Open | 0 | 0 | 0 | 0 |
| Open rural / Dense rural | §3.1 | §3.1 | 0 | 0 |
| Vegetation | SAALOS | SAALOS | SAALOS | SAALOS (clamped) |
| Suburban | §3.1 | §3.1 + §3.2 (max) | §3.2 | §3.2 (clamped) |
| Urban | §3.1 | §3.1 + §3.2 (max) | §3.2 | §3.2 (clamped) |

No user configuration is needed for this dispatch — the correct model is applied automatically based on the land-cover category and operating frequency.

### Clutter in Reports

Both P2P and coverage reports include clutter loss fields:

- `clutter_source`: describes where the clutter data came from (e.g. `override`, a raster path, or `fallback_open`)
- `clutter_method`: which sub-models were applied (e.g. `§3.1+§3.2/p833`)
- `clutter_percentile`: the location percentile used for §3.2 and BEL calculations
- `clutter_tx_db`: TX terminal clutter loss
- `clutter_rx_db`: RX terminal clutter loss
- `total_path_loss_db`: ITM loss plus both terminal clutter losses (excluding BEL)
- `bel_rx_db`: RX building entry loss from P.2109-2 (0.0 when BEL not enabled)
- `total_with_bel_db`: total path loss including clutter and BEL

For coverage, `itm_loss_db` and `total_path_loss_db` are grid-wide means over valid pixels.

Advanced inputs include:

- `N0`
- `epsilon`
- `sigma`

### Important Concept: Max Analysis Distance

`Max analysis distance (km)` is not the predicted coverage radius.

It tells NoWires how far from the transmitter it should compute the raster. The actual usable range is derived afterward from cells whose received signal is above the configured `RX sensitivity`.

### Grid Size Guidance

Available presets range from `64 x 64` to `1024 x 1024`.

- lower grid sizes run faster
- higher grid sizes look smoother but take longer
- large analysis distances combined with large grids can increase runtime noticeably

### Basic Steps

1. Open `Coverage Analysis`.
2. Select the transmitter point.
3. Set `Max analysis distance (km)`.
4. Choose a `Grid size resolution`.
5. Adjust `Overlay transparency (%)` if you want to see more or less basemap beneath the heatmap.
6. Enter radio parameters such as:
   - frequency
   - TX power
   - gains
   - RX sensitivity
7. Run the tool.
8. Review:
   - the output raster
   - the legend
   - the Processing log statistics

### Optional Coverage Report Export

Coverage analysis can also write:

- `CSV`
- `JSON`
- `HTML`
- `PDF` — rendered from the HTML template via Qt's `QTextDocument` + `QPrinter`. Falls back silently when Qt print support isn't available in the host install.

These exports contain the key coverage inputs plus the derived summary values, including usable distance metrics and received-signal statistics.

Coverage reports now also include:

- `fade_margin_class`
- `availability_method`
- `availability_estimate_pct` when the formal path is used
- `reliability_summary`
- `clutter_source`, `clutter_tx_db`, `clutter_rx_db`, and `total_path_loss_db` when clutter correction is enabled
- `itm_loss_db` (grid-wide mean over valid pixels)

Coverage can fall back more often than P2P because not every raster cell is a good candidate for the formal availability method.

### Adjusting Coverage Opacity

After a coverage run, you can open `NoWires -> Coverage Opacity` to adjust the most recent coverage raster without rerunning the algorithm.

If no coverage layer has been created yet, the plugin will warn you and ask you to run `Coverage Analysis` first.

### Previewing an Antenna Pattern

To sanity-check an antenna pattern CSV before referencing it from a P2P or Coverage run, open `NoWires -> Preview Antenna Pattern`. Click *Load pattern CSV…*, pick the file, and the dialog renders a polar plot (normalised so 0 dB is the peak) with 30° azimuth gridlines. Useful for catching swapped columns, wrong units, or files that don't wrap to 360°.

### Reading the Result

The tool reports:

- min usable distance
- max usable distance
- average usable distance
- percent of pixels above sensitivity
- min, max, and mean received signal

Transparent or faint areas usually indicate very weak or no service, depending on the rendered signal level and raster NoData behavior. Areas near the transmitter with the strongest signals appear as the darkest green (Very Strong, > -30 dBm).

The heatmap should track the same north-up orientation as the basemap and NoWires DEM. If a raster appears offset or upside down, make sure you are using a current plugin build and remove any older copy of the plugin before reinstalling.

## Basic Workflow: Coverage Comparison

Use this tool to compare two coverage configurations side-by-side and see where one provides stronger or weaker signal than the other.

### What It Produces

- A delta raster showing the difference in path loss between Panel A and Panel B (positive values mean Panel A has higher loss)
- Dual-panel statistics with min, max, mean, and standard deviation
- Optional CSV, JSON, and HTML reports

### Basic Steps

1. Open `Coverage Comparison` from the Processing Toolbox or the NoWires menu.
2. Configure Panel A parameters (TX point, frequency, power, heights, etc.).
3. Configure Panel B parameters (same TX point, potentially different radio settings).
4. Run the tool.
5. Review the delta raster and summary statistics.

### Interpreting the Delta Raster

- **Red/warm colours**: Panel A has higher path loss (Panel B is better in that area)
- **Blue/cool colours**: Panel A has lower path loss (Panel A is better in that area)
- **Near-zero values**: Both panels produce similar results

## Basic Workflow: Batch P2P Analysis

Use this tool to compute multiple point-to-point links in one run.

### Modes

- **One-to-Many**: A single TX point is paired with each RX point from a vector layer.
- **Many-to-One**: Each TX point from a vector layer is paired with a single RX point.

### What It Produces

- A combined vector layer with all link results ranked by link margin
- Link margin and path loss for each computed link
- Optional CSV and JSON reports

### Basic Steps

1. Open `Batch P2P Analysis` from the Processing Toolbox or the NoWires menu.
2. Select the mode (one-to-many or many-to-one).
3. Specify the fixed endpoint and the vector layer of opposite-end points.
4. Enter radio parameters (frequency, heights, power, gains, etc.).
5. Optionally configure antenna and clutter settings.
6. Run the tool.
7. Review the ranked results layer and optional report.

## Basic Workflow: Contour Lines

Use this tool to generate contours and an optional hillshade/elevation overlay from downloaded Copernicus GLO-30 DEM.

### Inputs

- area of interest extent
- contour interval
- units: metres or feet
- smoothing level
- line color
- optional elevation overlay

### Basic Steps

1. Open `Contour Lines`.
2. Draw or enter an area of interest.
3. Choose the contour interval and units.
4. Set smoothing.
5. Choose a line color.
6. Decide whether to generate the elevation overlay.
7. Run the tool.

## Basic Workflow: 3D View

Use this when you want to inspect the latest NoWires DEM, coverage raster, and contour output in a QGIS 3D scene.

### How It Works

- Coverage Analysis stores the latest coverage and DEM layers for 3D use.
- Contour Lines stores the latest contour layer and optional DEM layer for 3D use.
- `Open 3D View` reuses those tracked layers when available.

### Basic Steps

1. Run `Coverage Analysis` or `Contour Lines` first.
2. Open `NoWires -> Open 3D View`.
3. Choose either `Local terrain` or `Globe`.
4. Review the opened 3D scene.

### Windows Limitation

On Windows, NoWires does not open the 3D canvas directly because that QGIS API path is unstable in the current plugin context.

Instead:

1. Run `Coverage Analysis` or `Contour Lines`.
2. Open QGIS's native 3D view from `View -> 3D Map Views -> New 3D Map View`.
3. Use the tracked NoWires DEM layer as terrain, then add the other tracked NoWires layers to the scene as needed.

## Updating the Plugin

### Recommended: Update via ZIP

1. Download the latest `NoWires-X.Y.Z.zip` from [GitHub Releases](https://github.com/tedaks/nowires-qgis-plugin/releases).
2. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the new ZIP — QGIS replaces the previous version automatically.

### Alternative: Manual Update

1. Close QGIS.
2. Replace the installed `NoWires` folder inside your QGIS profile's `python/plugins` directory with the new version.
3. Start QGIS again.

## Removing the Plugin

1. Close QGIS.
2. Delete the `NoWires` folder from your QGIS profile's `python/plugins` directory.
3. Restart QGIS.

## Troubleshooting

### The plugin does not appear in QGIS

Check:

- the folder is named `NoWires`
- `metadata.txt` exists directly inside `NoWires`
- `__init__.py` exists directly inside `NoWires`
- the folder is inside the active profile's `python/plugins` directory

### The plugin appears but tools do not run

Check:

- QGIS version is 4.x
- internet access is available for DEM download
- the analysis area is not excessively large

### Coverage analysis is slow

NoWires uses multiprocessing on all three desktop platforms (Linux, macOS, Windows) by default. If the Processing dialog shows `Computing N pixels with K workers...`, multiprocessing is on. If instead it shows `Using single-threaded mode...`, the plugin couldn't validate a bootable Python interpreter for spawning — see [Multiprocessing falls back to sequential](#multiprocessing-falls-back-to-sequential) below.

Even with multiprocessing on, you can speed up runs further by:

- reducing max analysis distance
- using a smaller grid size
- simplifying directional antenna settings if not needed

For repeatable development-side checks, the repository also includes a synthetic runtime benchmark:

```bash
python3 benchmarks/coverage_runtime.py
```

### Multiprocessing falls back to sequential

NoWires probes a real Python interpreter under the QGIS app and validates it before enabling the worker pool. If the validation fails, you'll see `Using single-threaded mode...` in the Processing dialog log and `macOS:` / `Windows: no usable Python interpreter found for multiprocessing` in the QGIS **Log Messages Panel → NoWires** tab.

Workarounds:

- **`NOWIRES_PYTHON_EXE`** — explicitly point at a working Python 3 you have installed. Set the env var before launching QGIS:
  - macOS: `export NOWIRES_PYTHON_EXE=/opt/homebrew/bin/python3.12` then launch QGIS from the same shell.
  - Windows: set the env var in System Properties → Environment Variables, then restart QGIS. e.g. `NOWIRES_PYTHON_EXE=C:\Python312\pythonw.exe`.
- **`NOWIRES_MAX_WORKERS`** — caps worker count (default `min(os.cpu_count(), 16)`). Reduce if your machine is memory-constrained.

### DEM download problems

NoWires downloads Copernicus GLO-30 tiles from AWS Open Data. Network restrictions, proxy settings, or SSL inspection can interfere with downloads.

### Open 3D View does not open a scene on Windows

This is expected in the current release. Use QGIS's native `View -> 3D Map Views -> New 3D Map View` action instead after running a NoWires coverage or contour workflow, and use the NoWires DEM layer as terrain.

## Support Checklist

When reporting a problem, include:

- operating system
- QGIS version
- plugin version
- which tool you ran (P2P, Coverage, Coverage Comparison, Batch P2P, Contour Lines, etc.)
- the parameters you used
- the exact error message from the Processing log

## Further Reading

- Project overview: [README.md](README.md)
- Technical reference: [Technical_Documentation.md](Technical_Documentation.md)
- Third-party notices: [NOTICE.md](NOTICE.md)
