# NoWires User's Guide

## Overview

NoWires is a QGIS 4 plugin for:

- point-to-point radio link analysis
- coverage heatmap analysis
- contour line generation from Copernicus GLO-30 DEM data

This guide is for end users. It focuses on installation, setup, and basic workflows. For implementation details and engineering reference material, see [TECH-DOC.md](TECH-DOC.md).

## Before You Start

You will need:

- a computer running Windows, Linux, or macOS
- permission to install QGIS and copy files into your QGIS profile
- an internet connection for downloading QGIS, the plugin, and DEM tiles

## Install QGIS 4

Use the official QGIS download page:

- Main download page: https://qgis.org/download/
- Installation guide: https://version.qgis.org/resources/installation-guide/

As of April 22, 2026, the official QGIS website lists QGIS 4.x as the current release line. Always check the official QGIS page for the latest 4.x installer and platform-specific notes.

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

You can download the plugin in either of these ways:

### Option 1: Download ZIP

1. Open the GitHub repository page for NoWires.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the archive.

Important:

- The extracted plugin folder should be named `NoWires`.
- The files `__init__.py` and `metadata.txt` should be directly inside that folder.

### Option 2: Clone with Git

```bash
git clone <repository-url>
```

If needed, rename the cloned folder to `NoWires` before installing it into QGIS.

## Install the Plugin into QGIS

The safest cross-platform method is to use your active QGIS profile folder instead of guessing the path manually.

### Recommended Method: Open the Active Profile Folder

1. Start QGIS.
2. Open your active profile folder from QGIS.
   Typical places to look are:
   - `Settings` -> `User Profiles`
   - or another menu entry that opens the active profile folder directly
3. Inside the active profile folder, create this path if it does not already exist:

```text
python/plugins
```

4. Copy the `NoWires` folder into that `python/plugins` folder.

Result:

```text
<active-profile-folder>/python/plugins/NoWires
```

### Typical Profile Locations

These are common examples, but the active-profile-folder method above is more reliable:

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
  - `Coverage Opacity`
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

### What It Produces

- ITM path loss result
- link budget values
- Fresnel zone analysis
- vector outputs for the path and Fresnel geometry
- optional profile chart

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

### Adjusting Coverage Opacity

After a coverage run, you can open `NoWires -> Coverage Opacity` to adjust the most recent coverage raster without rerunning the algorithm.

If no coverage layer has been created yet, the plugin will warn you and ask you to run `Coverage Analysis` first.

### Reading the Result

The tool reports:

- min usable distance
- max usable distance
- average usable distance
- percent of pixels above sensitivity
- min, max, and mean received signal

Transparent or faint areas usually indicate very weak or no service, depending on the rendered signal level and raster NoData behavior.

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
3. Use the tracked NoWires DEM, coverage, and contour layers already added to the project.

## Updating the Plugin

To update manually from GitHub:

1. Close QGIS.
2. Replace the installed `NoWires` folder inside your QGIS profile's `python/plugins` directory.
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

Try:

- reducing max analysis distance
- using a smaller grid size
- simplifying directional antenna settings if not needed

For repeatable development-side checks, the repository also includes a synthetic runtime benchmark:

```bash
python3 benchmarks/coverage_runtime.py
```

### DEM download problems

NoWires downloads Copernicus GLO-30 tiles from AWS Open Data. Network restrictions, proxy settings, or SSL inspection can interfere with downloads.

### Open 3D View does not open a scene on Windows

This is expected in the current release. Use QGIS's native `View -> 3D Map Views -> New 3D Map View` action instead after running a NoWires coverage or contour workflow.

## Support Checklist

When reporting a problem, include:

- operating system
- QGIS version
- plugin version
- which tool you ran
- the parameters you used
- the exact error message from the Processing log

## Further Reading

- Project overview: [README.md](README.md)
- Technical reference: [TECH-DOC.md](TECH-DOC.md)
- Third-party notices: [NOTICE.md](NOTICE.md)
