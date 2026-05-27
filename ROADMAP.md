# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## Planned

### Broaden `__del__` exception guards

`ElevationGrid.__del__` (`elevation.py:222`) has no try/except — crashes during
interpreter shutdown with `AttributeError` when `__init__` was never called
(confirmed in Docker integration warnings). `SharedDEMGrid.__del__`
(`shared_dem_grid.py:190`) catches only `TypeError`, missing `AttributeError` for
late-shutdown GC where module globals are `None`. Add `(TypeError, AttributeError)`
to both, matching the pattern already in `TempDirManager.__del__`.

### Decompose functions over 100 lines

Ten functions exceed the 100-line single-responsibility threshold:
`build_coverage_tasks()` (189), `run_p2p_analysis()` (174),
`show_profile_chart()` (172), `download_tile_with_retry()` (166),
`add_panel_params()` (156), `_compute_single_link()` (145),
`write_fresnel_zone()` (117), `clutter_loss_saalos()` (110),
`build_coverage_report_payload_for_grid()` (108), `compute_coverage()` (106).

Each should split into 2-3 focused helpers per the 300-line file gate convention.

### Add type hints to `antenna.py`, `nowires.py`, and `radio.py`

These three core modules have the highest concentration of untyped function
arguments. The rest of the codebase is well-typed. Closing this gap would enable
`mypy --strict` on the full project.

### Remove dead `contour_shp_path is None` check in contour algorithm

`algorithm/contour.py:205-207` checks `if contour_shp_path is None` but
`generate_contour_lines()` (`contour/generation.py:71`) never returns `None` —
it either returns the path or raises `RuntimeError`. The `None` branch is
unreachable. Either remove it or replace with a feature-count validation.

### Reopenable P2P profile chart (MINOR)

Closing the P2P chart dock destroys the widget and drops all profile data —
the chart can only be recovered by re-running the algorithm. Store the last
`chart_kwargs` on the `show_profile_chart` module and add a "Reopen P2P Chart"
menu action so the graph is reopenable without recomputation.

### Project-relative output paths for temporary layers (PATCH)

When coverage or P2P is run as "Temporary Output", the raster and marker GPKG
are written to `/tmp/NoWires-<user>/`. The paths are stored in the QGIS project
file but `/tmp` is cleaned by `systemd-tmpfiles` on reboot — layers are missing
after reopen. Moving the project to another computer breaks the paths entirely.

**Affected paths:**

| Algorithm | File | Temporary output written to |
|-----------|------|----------------------------|
| Coverage | `algorithm/coverage.py:87` | `coverage_prx.tif` |
| Coverage | `algorithm/coverage.py:148` | `tx_marker.gpkg` |
| P2P | `p2p/compute.py:193` | `profile_line.gpkg`, `fresnel_poly.gpkg`, `markers.gpkg` |

DEM/WorldCover caches, intermediate merges, and contour outputs are already
transient or user-specified — not affected.

**Design:**

Extract a shared helper that detects whether the QGIS project has been saved:

```python
def _project_or_temp_dir(tmp_mgr, context, feedback, name):
    proj = context.project().fileName()
    if proj:
        out = os.path.join(os.path.dirname(proj), "nowires_" + name)
        os.makedirs(out, exist_ok=True)
        return out
    out = tmp_mgr.make_dir(name, persistent=True)
    tmp_mgr.warn_persistent(feedback)
    return out
```

- Saved project → write to `<project_dir>/nowires_coverage/` (or `nowires_p2p/`)
- Unsaved project → fall back to existing `/tmp` behavior

**Portability:** Cross-machine transfer works when the user enables QGIS project
settings → General → "Save paths as relative". QGIS normalises absolute paths to
`./nowires_coverage/` on save and resolves `./` relative to the project file on
open. Same-machine reboot survival works without any user action.

### ThreadPoolExecutor leak in tile_merge (PATCH)

`tile_merge.py:100-102` creates `ThreadPoolExecutor(max_workers=1)` per clipped tile
without `with` or explicit `shutdown()`. Orphan executors leave worker threads
parked in `concurrent.futures.thread._threads_queues` until interpreter shutdown,
so a 200-tile run accumulates ~200 idle threads. Fix: hoist a single module-level
executor reused across calls, or wrap the `.submit()` in a `with` block.

### Proxy auth wired only into Contour Lines (MINOR)

`setup_proxy_opener` is called from `algorithm/contour.py:161` only. Coverage, P2P,
Batch, and Comparison invoke `ensure_dem_for_area` and `ensure_clutter_grid_for_area`
without any proxy, so users behind authenticated proxies cannot run those four
algorithms. Add `QgsProcessingParameterAuthConfig` to each, thread `proxy_opener`
through `ensure_dem_for_area` (already supported) and through
`ensure_worldcover_for_area` → `download_worldcover_tiles` (parameter needs adding).

### Proxy realm host/port validation (PATCH)

`contour/pipeline.py:60-64` formats `proxy_base_url` from `parsed_realm.hostname`
and `.port` without a None check. A malformed realm URL (e.g. a bare hostname with
no scheme) yields `http://None:None` and downloads fail silently. Validate both
fields, surface a clear `feedback.pushWarning`, and return None instead of building
a broken opener.

### Contiguous DEM array after south-up flip (PATCH)

`elevation.py:143` assigns `self.data = self.data[::-1]`, producing a reversed
view rather than a contiguous copy. The sibling `clutter/grid.py:83` already does
`data[::-1].copy()` — match it (`np.ascontiguousarray(self.data[::-1])`) so the
bilinear hot path operates on contiguous memory.

### Split algorithm/coverage.py before next addition (PATCH)

`algorithm/coverage.py` is at exactly 300 lines — the AGENTS.md cap. Any new
helper or parameter forces an emergency extraction. Pre-emptively move
`_build_clutter_context` and `_write_coverage_outputs` into a new
`radio_coverage/coverage_outputs.py`. Golden-file tests
(`tests/test_report_export_golden.py`) verify zero behavior change.

### Remove dead try/finally in P2P algorithm (PATCH)

`algorithm/p2p.py:182-191` wraps `run_p2p_analysis(p2p_params)` in `try/finally`
where the finally body is `pass` plus an explanatory comment. The wrapper does
nothing — drop it and keep the comment near the call site.

### Document NoWires package-name requirement (PATCH)

`__init__.py:74` does `from NoWires.nowires import NoWiresPlugin` and every other
module uses `from NoWires.*` imports. The plugin install directory must be exactly
`NoWires` for any import to resolve — a clone into `nowires_qgis_plugin/` or any
QGIS-manager slug other than `NoWires` breaks the plugin. Either document the
requirement in README/INSTALL or convert to package-relative imports.

### K-factor parameter does not affect ITM propagation prediction (MINOR)

The P2P/Batch UI exposes `K_FACTOR_PRESET` with options labelled
"Sub-refractive / Geometric / Standard atmosphere / Super-refractive /
Strong super-refractive". The label strongly implies the value affects propagation
prediction; in fact it only affects Fresnel-zone/LOS curvature display.

**Call chain proves k_factor never reaches ITM:**

`itm_p2p_loss` (`radio.py:200-213`) signature accepts no `k_factor`:
```
itm_p2p_loss(h_tx, h_rx, profile, climate, N0, f__mhz, polarization,
             epsilon, sigma, mdvar, time_pct, location_pct, situation_pct)
```

All three callers omit it:
- `p2p/compute.py:141-144`
- `batch/outputs.py:105-118`
- `radio_coverage/compute.py:81-94`

`k_factor` is used only in:
- `fresnel.py:52,67,86,95` — `earth_bulge` and `fresnel_profile_analysis` (LOS curvature + Fresnel clearance geometry)
- `p2p/report_display.py:101`, `p2p/chart.py:116`, `report/payloads.py:84` — display attribution only

**Why this is not "pass k_factor to ITM":** The Longley-Rice ITM algorithm
derives its own effective Earth radius internally from surface refractivity N0;
that is how the standard works. The bundled `itm` package has no k_factor input
parameter. So the propagation prediction already responds to refractivity — it
just responds to N0, not to k.

**Fix options:**

1. **Relabel/document.** Rename the parameter "Fresnel Earth-radius factor" and
   add a tooltip explaining it affects only Fresnel/LOS display, not ITM loss.
   Direct users wanting to model anomalous refractivity to the N0 advanced ITM
   parameter. Smallest blast radius.
2. **Couple preset to N0.** Map each preset to a representative N0 value
   (sub-refractive → low N0, super-refractive → high N0) so changing the preset
   changes propagation prediction too. Requires care: presets currently let the
   user pick k independent of N0, and these two are physically related — coupling
   them removes a degree of freedom that some users may rely on. Use an opt-in
   "tie k-factor to N0" checkbox if going this route.

Either change must update the user-facing docs to remove the implication that k
affects propagation directly.

### BEL silently dropped in P2P/Batch simple-clutter mode (PATCH)

`compute_terminal_clutter_losses` (`clutter/advanced.py:165-222`) splits on
`advanced = context is not None and context.model == "advanced"`. The simple-mode
branch (`clutter/advanced.py:174-180`) returns a `TerminalClutterLosses` with
default `total_with_bel_db=0.0` and `rx_bel_db=0.0` — **BEL is never computed in
simple mode**.

P2P (`p2p/compute.py:184`) and Batch (`batch/outputs.py:140`) consume
`cl.total_with_bel_db` directly, so simple-clutter runs in those algorithms
produce byte-identical rasters/results whether BEL is enabled or disabled.

Coverage is unaffected: it computes BEL on a separate path
(`radio_coverage/tasks.py:127-135`) that fires in both simple and advanced modes.

**Fix:** When `context.bel_enabled` is True, call `building_entry_loss` from the
simple-mode branch at `clutter/advanced.py:174-180` and populate `rx_bel_db` /
`total_with_bel_db` before returning. Add a regression test that asserts
`total_with_bel_db > total_loss_db` for a simple-mode P2P link with BEL enabled.

### BEL gated on clutter_enabled across all algorithms (PATCH)

Even after fixing the simple-mode path above, BEL still requires
`clutter_enabled=True` to take effect:

- Coverage: gate at `radio_coverage/tasks.py:128`
  (`if clutter_enabled and clutter_context is not None and clutter_context.bel_enabled`)
- P2P: `clutter_context` is built only when `p.clutter_enabled` is True
  (`p2p/compute.py:174`); without it, BEL is skipped
- Batch: same gating via `params.clutter_enabled` (`batch/outputs.py:124`)

A user enabling BEL but leaving clutter off gets a byte-identical raster to a
BEL-off run, with no warning.

**Why this is wrong:** BEL models a receiver inside a building. It is
physically independent of outdoor terrain clutter — a rural receiver inside a
thermally-efficient building can have 25–35 dB BEL even when outdoor clutter
loss is zero. The current gating ties two unrelated effects.

**Fix:** Decouple BEL from `clutter_enabled`. Compute it whenever `bel_enabled`
is True, regardless of clutter state. Cleanest path: lift BEL out of the
clutter pipeline into a standalone helper that takes only the BEL inputs
(`frequency_mhz`, `bel_building_type`, `bel_elevation_angle_deg`, `percentile`)
and is applied to `prx` after the clutter total, with no precondition on
`clutter_enabled`. Update UI so BEL parameters are visible/enabled even when
"Clutter Correction" is off.

Add regression tests:
- P2P with `clutter_enabled=False, bel_enabled=True` produces non-zero BEL
- Coverage with `clutter_enabled=False, bel_enabled=True` produces a raster
  that differs from the same run with `bel_enabled=False`

### Omni-preset silent-snap warning (PATCH)

When `ANTENNA_PRESET=0` (Omni), `radio_coverage/params.py:220-223` forces
`antenna_az=None` and `antenna_bw_override=360.0` regardless of the
`ANTENNA_AZ`, `ANTENNA_BW`, and `DOWNTILT_DEG` values the user supplied. The
snap is intentional (omni means omni), but it is **silent** — the user gets no
feedback that their directional inputs were discarded.

**Evidence from run08:** four scenarios (`cov_antenna_downtilt`,
`cov_antenna_sector_65deg`, `cov_antenna_downtilt_only`,
`cov_antenna_sector_65deg_only`) all passed `ANTENNA_PRESET=0` with non-default
BW (65) or DOWNTILT (6) values, and produced byte-identical rasters to the
omni baseline (md5 `d3187996…`). A reasonable test author assumed the
parameters would take effect; the plugin gave no hint they had not.

**Fix:** When `ANTENNA_PRESET=0` and any of `ANTENNA_AZ`, `ANTENNA_BW != 360.0`,
or `DOWNTILT_DEG != 0.0` is set, emit a single `feedback.pushInfo` line such as:

> "Note: ANTENNA_BW=65.0 and DOWNTILT_DEG=6.0 ignored — preset=Omni snaps both
> to omnidirectional defaults. Choose preset=Custom (or a sector preset) to
> apply directional values."

Apply the same guard to the Comparison and Batch algorithms (which share
`shared_params.add_advanced_itm_params`). Add a regression test that asserts
the info line is pushed when the snap fires.


