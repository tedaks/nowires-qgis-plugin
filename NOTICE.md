# NoWires QGIS Plugin — Notice & Attribution

SPDX-License-Identifier: MIT

Copyright (c) 2026 Bortre Tenamo <tedaks@gmail.com>

This plugin combines original work with code adapted from MIT-licensed and
public-domain components. The plugin's own source is distributed under the
**MIT License** (see LICENSE); the files under `itm/` are US-Government public
domain (NTIA disclaimer). NoWires runs inside QGIS (GPL-2.0-or-later); MIT is
one-way compatible with the GPL, so the running combination inside QGIS is
governed by the GPL, which is normal for a QGIS plugin.

**License history:** releases up to and including 2.x were GPL-3.0-or-later
(the plugin then bundled GPL ContourLines-derived code). That code was removed
or clean-room reimplemented for 3.0.0; **only 3.0.0 and later are MIT.**
Pre-3.0.0 tags remain GPL.

---

## 1. nowires — Radio Propagation Analysis System

**Source:** <https://github.com/tedaks/nowires>  
**License:** MIT License  
**Copyright:** Copyright (c) 2024 NoWires Contributors

The following files are derived from or inspired by the nowires project (adapted from the FastAPI backend into QGIS Processing algorithms):

| Plugin file | Original source |
|---|---|
| `algorithm/coverage.py` | `apps/api/app/coverage.py`, `apps/api/app/coverage_render.py` |
| `algorithm/coverage_comparison.py` | `apps/api/app/coverage.py`, `apps/api/app/coverage_render.py` |
| `algorithm/p2p.py` | `apps/api/app/p2p.py` |

| `radio_coverage/engine.py` | `apps/api/app/coverage_workers.py`, `apps/api/app/coverage_render.py` |
| `radio.py` (ITM bridge, Fresnel, signal levels) | `apps/api/app/itm_bridge.py`, `apps/api/app/math_kernels.py`, `apps/api/app/signal_levels.py` |
| `antenna.py` | `apps/api/app/antenna.py` |
| `clutter/__init__.py`, `clutter/advanced.py`, `clutter/categories.py`, `clutter/constants.py`, `clutter/context.py`, `clutter/grid.py`, `clutter/resolve.py` | `apps/api/app/clutter/__init__.py` |
| `clutter/p833.py` | original code replacing previously-derived saalos model (see section 7) |
| `elevation.py` (terrain utilities, ElevationGrid) | `apps/api/app/elevation_grid.py`, `apps/api/app/terrain.py` |
| `radio_coverage/palette.py` (signal level palette) | `apps/api/app/signal_levels.py`, `apps/api/app/coverage_render.py` |

Original MIT license text:

> Copyright (c) 2024 NoWires Contributors
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

---

## 2. pyitm / itm — ITS Irregular Terrain Model (Longley-Rice)

**Source:** <https://github.com/tedaks/pyitm>  
**Intermediate upstream:** <https://github.com/tedaks/itm>  
**Origin:** <https://github.com/NTIA/itm>  
**License:** NTIA Software Disclaimer / Release (public domain for US Government works)  
**Copyright:** National Telecommunications and Information Administration (NTIA)

The `itm/` directory is bundled from the tedaks/pyitm repository with minimal local adaptations for plugin packaging, primarily import-path changes. The pyitm library is a pure-Python port of tedaks/itm, which in turn is based on NTIA's Irregular Terrain Model. The original ITM was developed by employees of the National Telecommunications and Information Administration (NTIA), an agency of the US Federal Government.

NTIA Disclaimer:

> This software was developed by employees of the National Telecommunications and Information Administration (NTIA), an agency of the Federal Government and is provided to you as a public service. Pursuant to Title 15 United States Code Section 105, works of NTIA employees are not subject to copyright protection within the United States.
>
> The software is provided by NTIA "AS IS." NTIA MAKES NO WARRANTY OF ANY KIND, EXPRESS, IMPLIED OR STATUTORY, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT AND DATA ACCURACY. NTIA does not warrant or make any representations regarding the use of the software or the results thereof, including but not limited to the correctness, accuracy, reliability or usefulness of the software.
>
> To the extent that NTIA holds rights in countries other than the United States, you are hereby granted the non-exclusive irrevocable and unconditional right to print, publish, prepare derivative works and distribute the NTIA software, in any medium, or authorize others to do so on your behalf, on a royalty-free basis throughout the World.
>
> You may improve, modify, and create derivative works of the software or any portion of the software, and you may copy and distribute such modifications or works. Modified works should carry a notice stating that you changed the software and should note the date and nature of any such change.
>
> You are solely responsible for determining the appropriateness of using and distributing the software and you assume all risks associated with its use, including but not limited to the risks and costs of program errors, compliance with applicable laws, damage to or loss of data, programs or equipment, and the unavailability or interruption of operation. This software is not intended to be used in any situation where a failure could cause risk of injury or damage to property.
>
> Please provide appropriate acknowledgments of NTIA's creation of the software in any copies or derivative works of this software.

---

## 3. ContourLines — removed in 3.0.0

The Contour Lines feature and **all** code derived from the GPL-licensed
ContourLines plugin (© 2023 Daniel Hulshof Saint Martin, forked at
<https://github.com/tedaks/ContourLines>) were **removed in 3.0.0** to make the
plugin's own source MIT.

- `algorithm/contour.py` and the `contour/` package were deleted.
- `dem_downloader.py` was previously listed here as ContourLines-derived. A
  review of the upstream ContourLines source found that the only derived portion
  was the **DEM tile-enumeration pattern** — dictated by the published Copernicus
  GLO-30 1°×1° tile grid and the QGIS geometry API (a thin, spec-driven
  expression, arguably *scène à faire*). It was independently reimplemented for
  3.0.0 from those public specifications (see §9 and CLEANROOM.md).
- `tile_download_base.py` was **never** ContourLines-derived. It was always the
  NoWires author's own download/retry/cache/integrity code, GPL-labeled only
  because the aggregate was GPL; it is MIT in 3.0.0. (It was conservatively
  reimplemented alongside `dem_downloader.py` — the source review confirmed this
  was unnecessary but harmless.)

No ContourLines-derived code remains in the 3.0.0+ distribution.

---

## 4. Copernicus DEM — Elevation Data

Elevation data used by this plugin is sourced from the **Copernicus GLO-30 Public DEM** hosted on AWS Open Data:

- Registry: <https://registry.opendata.aws/copernicus-dem/>
- Documentation: <https://copernicus-dem-30m.s3.amazonaws.com/readme.html>

**Attribution:**  
Copernicus DEM © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

**Licence:**  
GLO-30 Public is available free of charge for any use under the terms of the [Copernicus DEM licence](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM).

---

## 5. ESA WorldCover 2020 v100 — Land-Cover Data

Land-cover data used for clutter correction is sourced from **ESA WorldCover 2020 v100**:

- Data access: <https://esa-worldcover.org/en/data-access>
- Download endpoint used by the plugin: <https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/>
- Dataset DOI: <https://doi.org/10.5281/zenodo.5571936>

**License:** Creative Commons Attribution 4.0 International (CC BY 4.0), available at <https://creativecommons.org/licenses/by/4.0/>.

**Attribution:**  
© ESA WorldCover project / Contains modified Copernicus Sentinel data (2020) processed by ESA WorldCover consortium.

Recommended citation:

> Zanaga, D., Van De Kerchove, R., De Keersmaecker, W., Souverijns, N., Brockmann, C., Quast, R., Wevers, J., Grosu, A., Paccini, A., Vergnaud, S., Cartus, O., Santoro, M., Fritz, S., Georgieva, I., Lesiv, M., Carter, S., Herold, M., Li, Linlin, Tsendbazar, N.E., Ramoino, F., Arino, O., 2021. ESA WorldCover 10 m 2020 v100. <https://doi.org/10.5281/zenodo.5571936>

---

## 6. ITM References

The Irregular Terrain Model was originally developed by:

- G.A. Hufford, *The ITS Irregular Terrain Model, version 1.2.2 Algorithm*
- G.A. Hufford, *The Irregular Terrain Model*
- A.G. Longley and P.L. Rice, *Prediction of Tropospheric Radio Transmission Loss Over Irregular Terrain*, NTIA Technical Report ERL 79-ITS 67, July 1968

---

## 7. Vegetation Clutter Model — ITU-R P.833

The vegetation clutter-loss model in `clutter/p833.py` implements the Am
(maximum woodland attenuation) value from §2.1 of ITU-R Recommendation P.833-9
(2016), "Attenuation in vegetation." P.833-9 §2.1 states that Am is "equivalent
to the clutter loss often quoted for a terminal obstructed by some form of ground
cover or clutter." Am = A1 · f^α uses the St. Petersburg fit (A1=1.37, α=0.42)
cited in P.833-9 §2.1 for mixed coniferous-deciduous forest, 105.9–2117.5 MHz.
The implementation is original code; no third-party source code was used.

ITU-R Recommendations are freely published by the International Telecommunication
Union.

---

## 8. Project Assets

`logo.png` is Original NoWires project artwork by Bortre Tenamo and is distributed as part of this MIT-licensed plugin.

---

## 9. Local Modifications

- Files adapted from `nowires` retain the original MIT attribution in this notice and are redistributed as part of this MIT-licensed plugin.
- `tile_download_base.py` and `worldcover_downloader.py` are original NoWires work (previously GPL-labeled only by aggregate); `tile_download_base.py` was **never** ContourLines-derived. `dem_downloader.py` is original work whose only previously-ContourLines-derived portion — the spec-driven DEM tile-enumeration pattern — was independently reimplemented for 3.0.0 (see §3 and CLEANROOM.md). All three are MIT in 3.0.0.
- Files in `itm/` are derived from `pyitm` and carry local import-path adjustments for plugin packaging. These modified works should not be treated as verbatim upstream copies.
- The saalos vegetation model (`clutter/saalos.py`, `clutter/_saalos_vec.py`) was removed in v2.0.0 and replaced with original code based on ITU-R P.833-9 (§7).
- The Contour Lines feature and all ContourLines-derived code were removed in 3.0.0 (see §3).
